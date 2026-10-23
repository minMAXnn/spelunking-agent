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
import { makeReasoner, buildBaselinePrompt } from './reason.js';
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
    // The same Worker answers at its workers.dev hostname and under a path on the site's origin.
    // Strip the mount point so every route below is written once, as an absolute path.
    const base = (env.BASE_PATH || '').replace(/\/+$/, '');
    let p = url.pathname;
    if (base && (p === base || p.startsWith(base + '/'))) p = p.slice(base.length);
    const path = p.replace(/\/+$/, '') || '/';
    const here = base ? `${url.origin}${base}` : url.origin;

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
        return new Response(page(env, base), { headers: { 'content-type': 'text/html; charset=utf-8' } });
      }

      if (path === '/health') {
        return json({
          ok: true,
          site: env.SITE || 'https://spelunking.ai',
          reasoner: env.ANTHROPIC_API_KEY ? env.ANTHROPIC_MODEL || 'claude-sonnet-4-5' : env.MODEL,
          can_forward_to_human: Boolean(env.SPK_API_KEY),
          // `saves_runs: true` read as "this app keeps your questions", which was accurate and
          // alarming, and it was also the only public hint that the front page's "Nothing is
          // stored" was false. Say the actual policy instead of whether a binding exists.
          run_storage: env.RUNS
            ? 'opt-in per request (store:true); kept 30 days and readable by anyone with the link. Off by default.'
            : 'no KV namespace bound, so no run is ever saved',
          stores_by_default: false,
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
          directives: Array.isArray(body.directives) ? body.directives : [],
        });
        // Storing is OPT-IN, and the default is off.
        //
        // This used to save every run unconditionally for 30 days, readable by anyone with the id,
        // while the reasoner on the site's own front page told visitors "Nothing is stored". That
        // sentence was written about the site's stateless frame endpoint and then applied to this
        // app, which is a different component with different behaviour — the same mistake as the
        // privacy text that promised a deletion living in another plugin.
        //
        // A question worth bringing here is often one the caller would not publish. So the default
        // is not to keep it, and a caller that wants a reopenable link asks for one. An id is only
        // returned when there is actually something behind it; handing back an id for a run that
        // was never saved would be its own small lie.
        const keep = body.store === true && Boolean(env.RUNS);
        if (keep) {
          run.id = rid();
          ctx.waitUntil(save(env, run.id, run));
        }
        run.stored = keep;
        run.retention = keep
          ? 'Kept for 30 days so this run can be reopened by its link, then deleted. Anyone holding the link can read it.'
          : 'Not stored. This run exists only in this response — nothing was written and there is no link to it.';
        return json(run);
      }

      // The control condition, for measuring whether the frame is worth anything.
      //
      // Same model, same adapter, same parser, fair prompt, no frame and no shape check. It exists
      // so "structure improves reasoning" is a claim we can test rather than one we assert, and it
      // is public because an evaluation you cannot reproduce is marketing. Nothing is stored.
      //
      // Deliberately not the default and not linked from the app: it is the measuring stick, not
      // the product. If it turns out the frame adds nothing, that is a finding we publish.
      if (path === '/api/baseline' && request.method === 'POST') {
        const body = await request.json().catch(() => ({}));
        const question = (body.question || '').toString().trim();
        if (question.length < 10) return json({ error: 'give me the question in a sentence at least' }, 400);
        const reason = makeReasoner(env, buildBaselinePrompt);
        const out = await reason({ question });
        return json({
          question,
          condition: 'baseline',
          answers: out.answers,
          resolution: out.resolution,
          model: out.model,
          honesty: {
            reasoned_by: out.model,
            framed_by: null,
            checked: 'nothing — this is the control condition and no shape check was run',
            not_checked: 'Everything. This output exists to be compared against the framed condition, not to be relied on.',
          },
          stored: false,
        });
      }

      // Just the frame, for a caller that wants to do its own thinking. This is the honest
      // default for another AI: it gets the structure and keeps the judgement.
      if (path === '/api/frame' && request.method === 'POST') {
        const body = await request.json().catch(() => ({}));
        // `directives` lets a caller overrule the site's keyword detection, which is blunt and
        // sometimes wrong. Dropping it here silently ignored the override and handed the model a
        // frame the caller had explicitly rejected — the frame steers the answer, so that mattered.
        return json(await api(env.SITE || 'https://spelunking.ai', '/covenant/deliberate', { question: body.question, directives: body.directives || [] }));
      }

      if (path === '/api/check' && request.method === 'POST') {
        const body = await request.json().catch(() => ({}));
        return json(
          await api(env.SITE || 'https://spelunking.ai', '/covenant/deliberate/check', {
            question: body.question,
            answers: body.answers || {},
            resolution: body.resolution || '',
            directives: body.directives || [],
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
