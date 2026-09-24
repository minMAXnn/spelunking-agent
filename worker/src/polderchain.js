/**
 * The loop.
 *
 *   frame  ->  reason  ->  shape-check  ->  (repeat while something is missing)  ->  verdict
 *
 * spelunking.ai supplies the frame and the shape-check. This app supplies the reasoning. That
 * split is deliberate and is stated in every answer: the site never judges whether a conclusion
 * is right, and this app must never imply that it did. The site checks that the work was done;
 * the thinking, and the responsibility for it, belong to whoever is driving.
 */

const MAX_PASSES = 3;

export async function api(site, path, body, opts = {}) {
  const r = await fetch(`${site}/wp-json/spelunking/v1${path}`, {
    method: body ? 'POST' : 'GET',
    headers: {
      'content-type': 'application/json',
      accept: 'application/json',
      'user-agent': 'spelunking-agent-app (+https://github.com/minMAXnn/spelunking-agent)',
      ...(opts.key ? { authorization: `Bearer ${opts.key}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await r.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    throw new Error(`${path} returned ${r.status} and not JSON`);
  }
  if (!r.ok) {
    const msg = json?.message || json?.error || `${path} failed with ${r.status}`;
    const err = new Error(msg);
    err.status = r.status;
    err.body = json;
    throw err;
  }
  return json;
}

/**
 * Run a question all the way through. Returns the whole trace, not just the verdict — the
 * working is the point, and a conclusion you cannot inspect is worth very little.
 */
export async function solve(env, question, { reason, maxPasses = MAX_PASSES, onStep } = {}) {
  const site = env.SITE || 'https://spelunking.ai';
  const trace = [];
  const step = (s) => {
    trace.push({ ...s, at: new Date().toISOString() });
    onStep?.(s);
  };

  const frame = await api(site, '/covenant/deliberate', { question });
  step({ step: 'frame', directives: frame.in_tension.map((d) => d.id), must_answer: frame.must_answer.map((q) => q.id) });

  let answers = {};
  let resolution = '';
  let check = null;
  let model = null;

  for (let pass = 1; pass <= maxPasses; pass++) {
    const out = await reason({ question, frame, answers, resolution, missing: check?.missing ?? [], pass });
    model = out.model;
    answers = { ...answers, ...(out.answers || {}) };
    resolution = out.resolution || resolution;
    step({ step: 'reason', pass, model, keys: Object.keys(out.answers || {}) });

    check = await api(site, '/covenant/deliberate/check', { question, answers, resolution });
    step({ step: 'check', pass, complete: check.complete, missing: check.missing?.length ?? 0, needs_human: check.needs_human });

    if (check.complete) break;
  }

  return {
    question,
    frame,
    answers,
    resolution,
    check,
    model,
    trace,
    // Said once, here, so every consumer of this object carries it.
    honesty: {
      reasoned_by: model,
      framed_by: `${site} — the Covenant's structure, quoted`,
      checked: 'shape only',
      not_checked:
        'Whether the conclusion is right. spelunking.ai checked that every Directive in tension was addressed and every required question answered. It did not evaluate the answer, and neither this app nor that site can tell you it is correct.',
    },
  };
}

/** Forward to a human on the site. Needs a registered key; registration is open and free. */
export async function forward(env, { question, work, ask, key }) {
  const site = env.SITE || 'https://spelunking.ai';
  if (!key) throw new Error('forwarding to a human needs a registered api key (SPK_API_KEY)');
  return api(site, '/covenant/deliberate/open', { question, work, rung: 'human', ask }, { key });
}

export async function poll(env, id, key) {
  const site = env.SITE || 'https://spelunking.ai';
  return api(site, `/covenant/deliberate/${id}`, null, { key });
}
