/**
 * Polderchain, as an app.
 *
 * Send it a problem. It fetches the Covenant's frame from spelunking.ai, reasons against that
 * frame, has the site check the shape of the result, and loops until nothing is missing. When
 * the structure runs out — when the honest answer needs something only a person knows — it says
 * so, and can hand the question to a human instead of inventing an answer.
 *
 * Two callers, one protocol: a person typing into the page, and an AI POSTing to /api/solve.
 */
import { solve, forward, poll, api } from './polderchain.js';
import { makeReasoner } from './reason.js';
import { page } from './ui.js';

const json = (data, status = 200) =>
  new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
      'access-control-allow-origin': '*',
      'x-reasoning-by': 'this app, not spelunking.ai',
    },
  });

const rid = () => crypto.randomUUID().replace(/-/g, '').slice(0, 16);

async function save(env, id, run) {
  if (!env.RUNS) return false;
  try {
    await env.RUNS.put(`run:${id}`, JSON.stringify(run), { expirationTtl: 60 * 60 * 24 * 30 });
    return true;
  } catch {
    return false; // a missing KV binding must not cost someone their answer
  }
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, '') || '/';

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'access-control-allow-origin': '*',
          'access-control-allow-methods': 'GET,POST,OPTIONS',
          'access-control-allow-headers': 'content-type,authorization',
        },
      });
    }

    try {
      if (path === '/' && request.method === 'GET') {
        return new Response(page(env), { headers: { 'content-type': 'text/html; charset=utf-8' } });
      }

      if (path === '/health') {
        return json({
          ok: true,
          site: env.SITE || 'https://spelunking.ai',
          reasoner: env.ANTHROPIC_API_KEY ? env.ANTHROPIC_MODEL || 'claude-sonnet-4-5' : env.MODEL,
          can_forward_to_human: Boolean(env.SPK_API_KEY),
          saves_runs: Boolean(env.RUNS),
        });
      }

      // The whole loop. This is the app.
      if (path === '/api/solve' && request.method === 'POST') {
        const body = await request.json().catch(() => ({}));
        const question = (body.question || '').toString().trim();
        if (question.length < 10) return json({ error: 'give me the question in a sentence at least' }, 400);

        const run = await solve(env, question, {
          reason: makeReasoner(env),
          maxPasses: Math.min(3, Math.max(1, Number(body.passes) || 3)),
        });
        run.id = rid();
        ctx.waitUntil(save(env, run.id, run));
        return json(run);
      }

      // Just the frame, for a caller that wants to do its own thinking. This is the honest
      // default for another AI: it gets the structure and keeps the judgement.
      if (path === '/api/frame' && request.method === 'POST') {
        const body = await request.json().catch(() => ({}));
        return json(await api(env.SITE || 'https://spelunking.ai', '/covenant/deliberate', { question: body.question }));
      }

      if (path === '/api/check' && request.method === 'POST') {
        const body = await request.json().catch(() => ({}));
        return json(
          await api(env.SITE || 'https://spelunking.ai', '/covenant/deliberate/check', {
            question: body.question,
            answers: body.answers || {},
            resolution: body.resolution || '',
          })
        );
      }

      if (path.startsWith('/api/run/') && request.method === 'GET') {
        const id = path.split('/').pop();
        if (!env.RUNS) return json({ error: 'no KV namespace bound, so runs are not saved' }, 501);
        const raw = await env.RUNS.get(`run:${id}`);
        return raw ? json(JSON.parse(raw)) : json({ error: 'no such run (they expire after 30 days)' }, 404);
      }

      // Hand it to a person on the site.
      if (path === '/api/forward' && request.method === 'POST') {
        const body = await request.json().catch(() => ({}));
        if (!env.SPK_API_KEY) {
          return json(
            {
              error: 'this app has no registered key, so it cannot forward to a human',
              fix: 'register at https://spelunking.ai/agents and set it: npx wrangler secret put SPK_API_KEY',
            },
            501
          );
        }
        const out = await forward(env, {
          question: body.question,
          work: { answers: body.answers, resolution: body.resolution, check: body.check },
          ask: body.ask,
          key: env.SPK_API_KEY,
        });
        return json(out);
      }

      if (path.startsWith('/api/status/') && request.method === 'GET') {
        const id = Number(path.split('/').pop());
        if (!env.SPK_API_KEY) return json({ error: 'no registered key configured' }, 501);
        return json(await poll(env, id, env.SPK_API_KEY));
      }

      return json({ error: 'not found', routes: ['GET /', 'GET /health', 'POST /api/solve', 'POST /api/frame', 'POST /api/check', 'POST /api/forward', 'GET /api/run/{id}', 'GET /api/status/{id}'] }, 404);
    } catch (err) {
      // Never dress a failure up as an answer.
      return json({ error: err.message || 'something went wrong', status: err.status ?? 500 }, err.status && err.status < 500 ? err.status : 500);
    }
  },
};
