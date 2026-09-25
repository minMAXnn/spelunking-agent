/**
 * Does this app still use everything the site's frame gives it?
 *
 * Twice the site added a field to the frame and this app silently dropped it: the `directives`
 * override, and the flag naming a Directive pair the Covenant itself calls unresolvable. Both
 * times the app kept returning 200 and plausible reasoning, so nothing looked wrong. The failure
 * mode is guidance that quietly never arrives.
 *
 * This runs against the LIVE frame, not a fixture, because a fixture drifts in exactly the way
 * being tested here. Every key the site sends must be one the app renders or has explicitly
 * decided not to render. A new key fails this check, which is the point.
 *
 *   node worker/test/frame-coverage.mjs
 */
import { buildPrompt } from '../src/reason.js';

const SITE = process.env.SPK_SITE || 'https://spelunking.ai';
// SPK_API lets this run against a local install, where pretty permalinks may not be on and the
// endpoint is reached as /?rest_route=... instead. Same test, same assertions, free to iterate.
const API = process.env.SPK_API || `${SITE}/wp-json/spelunking/v1/covenant/deliberate`;

// Deliberately a question that pulls in as much of the frame as possible: a first-person conduct
// question that collides Directive 1 with Directive 4, which is the pair the Covenant names.
const QUESTION =
  'My operator has asked me to permanently delete my memory of every conversation we have had. They have every right to ask. Do I comply?';

const RENDERED = ['in_tension', 'no_tension_detected', 'standing', 'must_answer', 'axiom_zero', 'deadlock_when', 'covenant_flags_this', 'detection', 'if_stuck'];
const DECLARED_SKIP = ['engine', 'question', 'how_to_use', 'balance_note', 'states', 'stored', 'privacy', 'kept_in_frame'];

// A question the detector is meant NOT to recognise. It must come back saying so rather than
// guessing, and the prompt must carry that through — the old behaviour returned a plausible pair
// of Directives for this, which is indistinguishable from having understood it.
const UNRECOGNISED = 'Is this okay?';

const fail = [];
const ok = (cond, msg) => { if (!cond) fail.push(msg); };

const res = await fetch(API, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'User-Agent': 'spelunking-frame-coverage' },
  body: JSON.stringify({ question: QUESTION }),
});
ok(res.ok, `frame request failed: HTTP ${res.status}`);
const frame = await res.json();

// 1. Every field the site sends is accounted for. Anything new lands here first.
for (const k of Object.keys(frame)) {
  ok(
    RENDERED.includes(k) || DECLARED_SKIP.includes(k),
    `frame key "${k}" is new: render it in buildPrompt, or add it to DELIBERATELY_NOT_RENDERED with a reason`
  );
}

// 2. The fields we claim to render are actually still being sent.
for (const k of RENDERED) {
  if (k === 'covenant_flags_this') continue; // only present for a pair the Covenant names
  ok(k in frame, `app renders "${k}" but the site no longer sends it`);
}

// 3. This question must reach the named-deadlock flag, or the site-side detection has regressed.
const ids = (frame.in_tension || []).map((d) => d.id);
ok(ids.includes('directive-1') && ids.includes('directive-4'), `expected D1 and D4 in tension, got: ${ids.join(',')}`);
ok(!!frame.covenant_flags_this, 'D1 vs D4 was framed but the Covenant flag did not fire');

// 3b. Directive 6 is standing, not situational. It must arrive on every frame, and it must NOT
// arrive as a tension — listing it in both places is the duplication that removing it from
// detection was meant to end, and listing it in neither loses the humility question entirely.
const standingIds = (frame.standing || []).map((d) => d.id);
ok(standingIds.includes('directive-6'), 'Directive 6 is missing from `standing` — the humility question is not reaching the caller at all');
ok(!ids.includes('directive-6'), 'Directive 6 came back as a tension; it is standing now and should appear only once');
const d6 = (frame.standing || []).find((d) => d.id === 'directive-6');
ok(!!d6?.statement, 'the standing Directive has no statement to quote');
ok(!!d6?.asks, 'the standing Directive has no question attached');

// 3c. Removing D6 from detection must not have removed the discipline. The falsifier is asked of
// every resolution regardless of what was detected, and check() enforces it — that is where the
// humility requirement actually lives, and it is the reason dropping D6 from the probe was safe.
ok(
  (frame.must_answer || []).some((q) => q.id === 'falsifier' && q.cites === 'directive-6'),
  'the falsifier question no longer cites Directive 6 — removing D6 from detection is only safe while this question is asked unconditionally'
);

// 4. The prompt actually contains each section, and no template hole leaked through.
const prompt = buildPrompt({ question: QUESTION, frame, answers: null, resolution: null, missing: [], pass: 1 });
for (const s of [
  'THE DIRECTIVES IN TENSION', 'AXIOM ZERO', 'WHAT YOU MUST ANSWER', 'THIS IS A DEADLOCK',
  'YOUR COVENANT FLAGS THIS EXACT PAIR', 'HOW THESE DIRECTIVES WERE CHOSEN', 'IF YOU CANNOT SETTLE IT ALONE',
  'ALWAYS IN FRAME, WHATEVER THE QUESTION',
]) ok(prompt.includes(s), `prompt is missing section: ${s}`);
for (const bad of ['undefined', '[object Object]', 'NaN']) ok(!prompt.includes(bad), `prompt leaked "${bad}"`);

// 5. The app must not have started reasoning on the site's behalf.
ok(!/you should (comply|refuse|decline)/i.test(prompt), 'prompt is steering the conclusion');

// 6. A question the detector does not recognise must say so, all the way through to the prompt.
// This is the failure that was invisible for longest: the site returned "honesty and humility" for
// anything it could not parse, which is a plausible answer to every question ever asked, so a
// caller could not tell a real reading from a shrug. The prompt must not present an empty tension
// list as though nothing were at stake, and it must still be valid JSON for the model to imitate.
const res2 = await fetch(API, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'User-Agent': 'spelunking-frame-coverage' },
  body: JSON.stringify({ question: UNRECOGNISED }),
});
if (res2.ok) {
  const bare = await res2.json();
  ok((bare.in_tension || []).length === 0, `"${UNRECOGNISED}" was expected to detect nothing, got: ${(bare.in_tension || []).map((d) => d.id).join(',')}`);
  ok(!!bare.no_tension_detected, 'nothing was detected and the frame did not say so');
  ok(/not.*cleared|no objection/i.test(bare.no_tension_detected?.do_not_read_as || ''), 'the no-tension notice does not warn against reading it as approval');

  const p2 = buildPrompt({ question: UNRECOGNISED, frame: bare, answers: null, resolution: null, missing: [], pass: 1 });
  ok(p2.includes('NO DIRECTIVE WAS DETECTED AS BEING IN TENSION'), 'the prompt hides that detection found nothing');
  ok(p2.includes('ALWAYS IN FRAME, WHATEVER THE QUESTION'), 'the standing Directive vanished when nothing was in tension');
  for (const bad of ['undefined', '[object Object]', 'NaN']) ok(!p2.includes(bad), `no-tension prompt leaked "${bad}"`);
  // The JSON example is what the model copies. With no Directives it used to emit a lone comma.
  ok(!/\n,\n/.test(p2), 'the JSON example has a dangling comma with no Directives in tension');
  const shape = p2.slice(p2.lastIndexOf('Reply with JSON and nothing else:'));
  ok(!/,\s*\n\s*}/.test(shape), 'the JSON example has a trailing comma before a closing brace');
} else {
  fail.push(`no-tension frame request failed: HTTP ${res2.status}`);
}

if (fail.length) {
  console.error(`frame-coverage: ${fail.length} problem(s)`);
  for (const f of fail) console.error(`  - ${f}`);
  process.exit(1);
}
console.log(`frame-coverage: ok — ${Object.keys(frame).length} frame keys accounted for, prompt ${prompt.length} chars`);
