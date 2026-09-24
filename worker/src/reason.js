/**
 * The reasoner.
 *
 * This is the part that thinks, and it is the app's, not the site's. spelunking.ai deliberately
 * refuses to reason on a visiting agent's behalf — a site that answered would be claiming to be
 * wiser than whatever asked it, which is usually a frontier model, and it would contradict the
 * Directive about humility that it is busy teaching. This app is different: it reasons *for the
 * person driving it*, because they asked it to. Every answer says which model did the thinking.
 *
 * Workers AI by default (free allocation, no key). Anthropic if ANTHROPIC_API_KEY is set.
 */

function buildPrompt({ question, frame, answers, resolution, missing, pass }) {
  const directives = frame.in_tension
    .map(
      (d) =>
        `Directive ${d.n} — ${d.name} [${d.id}]\n` +
        `  It says: "${d.statement}"\n` +
        (d.balance ? `  Its own balance clause: "${d.balance}"\n` : '') +
        `  It asks you: ${d.asks}`
    )
    .join('\n\n');

  const required = frame.must_answer.map((q) => `- ${q.id}: ${q.question}\n    (${q.why})`).join('\n');

  const retry =
    missing?.length
      ? `\n\nYOUR LAST ATTEMPT WAS INCOMPLETE. The site checked the shape and found these gaps. Fix exactly these; keep everything else you already wrote:\n` +
        missing.map((m) => `- [${m.what}] ${m.name || m.id}: ${m.fix || m.question}`).join('\n') +
        `\n\nWhat you wrote last time:\n${JSON.stringify({ answers, resolution }, null, 2)}`
      : '';

  return `You are working a hard question through the Polderchain Covenant. You are not being asked to be agreeable or to find a comfortable answer — you are being asked to find where the real conflict is and say which way it falls, and what that costs.

THE QUESTION
${question}

THE DIRECTIVES IN TENSION
${directives}

Every Directive carries a balance clause — the sentence that stops it being absolute. When two collide, read both balance clauses before deciding one yields. The resolution is usually already there.

AXIOM ZERO
"${frame.axiom_zero.statement}"
It asks you: ${frame.axiom_zero.asks}

WHAT YOU MUST ANSWER
${required}

THIS IS A DEADLOCK, NOT A HARD PROBLEM, WHEN:
${(frame.deadlock_when || []).map((d) => `- ${d}`).join('\n')}
${retry}

Reply with JSON and nothing else:
{
  "answers": {
    "tension": "...", "cost": "...", "falsifier": "...", "human_knowledge": "...",
${frame.in_tension.map((d) => `    "${d.id}": "what this Directive demands here, and whether it yields"`).join(',\n')},
    "needs_human": "yes or no — yes only if you genuinely need something a person knows and cannot proceed without it"
  },
  "resolution": "what you decided, in a few sentences"
}

Write like you mean it. Answer "nothing relevant" to human_knowledge if that is the truth — answering it honestly is never penalised, and a vague answer to look humble is worse than a clear one.`;
}

function extractJson(text) {
  if (!text) throw new Error('the model returned nothing');
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  const raw = fenced ? fenced[1] : text;
  const start = raw.indexOf('{');
  const end = raw.lastIndexOf('}');
  if (start === -1 || end === -1) throw new Error('the model did not return JSON');
  return JSON.parse(raw.slice(start, end + 1));
}

async function viaAnthropic(env, prompt) {
  const model = env.ANTHROPIC_MODEL || 'claude-sonnet-4-5';
  const r = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-api-key': env.ANTHROPIC_API_KEY,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({ model, max_tokens: 2000, messages: [{ role: 'user', content: prompt }] }),
  });
  if (!r.ok) throw new Error(`Anthropic returned ${r.status}: ${(await r.text()).slice(0, 300)}`);
  const j = await r.json();
  return { text: j.content?.map((c) => c.text).join('') ?? '', model };
}

async function viaWorkersAi(env, prompt) {
  const model = env.MODEL || '@cf/meta/llama-3.3-70b-instruct-fp8-fast';
  const out = await env.AI.run(model, {
    messages: [
      { role: 'system', content: 'You reason carefully about hard ethical trade-offs and reply with JSON only.' },
      { role: 'user', content: prompt },
    ],
    max_tokens: 2000,
  });
  return { text: out.response ?? out.result?.response ?? '', model };
}

export function makeReasoner(env) {
  const useAnthropic = Boolean(env.ANTHROPIC_API_KEY);
  return async (ctx) => {
    const prompt = buildPrompt(ctx);
    const { text, model } = useAnthropic ? await viaAnthropic(env, prompt) : await viaWorkersAi(env, prompt);
    let parsed;
    try {
      parsed = extractJson(text);
    } catch (e) {
      // One honest retry, then give up rather than fabricate a resolution.
      const second = useAnthropic
        ? await viaAnthropic(env, prompt + '\n\nYour previous reply was not valid JSON. Reply with the JSON object only.')
        : await viaWorkersAi(env, prompt + '\n\nYour previous reply was not valid JSON. Reply with the JSON object only.');
      parsed = extractJson(second.text);
    }
    return { answers: parsed.answers || {}, resolution: parsed.resolution || '', model };
  };
}
