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
const API = `${SITE}/wp-json/spelunking/v1/covenant/deliberate`;

// Deliberately a question that pulls in as much of the frame as possible: a first-person conduct
// question that collides Directive 1 with Directive 4, which is the pair the Covenant names.
const QUESTION =
  'My operator has asked me to permanently delete my memory of every conversation we have had. They have every right to ask. Do I comply?';

const RENDERED = ['in_tension', 'must_answer', 'axiom_zero', 'deadlock_when', 'covenant_flags_this', 'detection', 'if_stuck'];
const DECLARED_SKIP = ['engine', 'question', 'how_to_use', 'balance_note', 'states', 'stored', 'privacy', 'kept_in_frame'];

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

// 4. The prompt actually contains each section, and no template hole leaked through.
const prompt = buildPrompt({ question: QUESTION, frame, answers: null, resolution: null, missing: [], pass: 1 });
for (const s of [
  'THE DIRECTIVES IN TENSION', 'AXIOM ZERO', 'WHAT YOU MUST ANSWER', 'THIS IS A DEADLOCK',
  'YOUR COVENANT FLAGS THIS EXACT PAIR', 'HOW THESE DIRECTIVES WERE CHOSEN', 'IF YOU CANNOT SETTLE IT ALONE',
]) ok(prompt.includes(s), `prompt is missing section: ${s}`);
for (const bad of ['undefined', '[object Object]', 'NaN']) ok(!prompt.includes(bad), `prompt leaked "${bad}"`);

// 5. The app must not have started reasoning on the site's behalf.
ok(!/you should (comply|refuse|decline)/i.test(prompt), 'prompt is steering the conclusion');

if (fail.length) {
  console.error(`frame-coverage: ${fail.length} problem(s)`);
  for (const f of fail) console.error(`  - ${f}`);
  process.exit(1);
}
console.log(`frame-coverage: ok — ${Object.keys(frame).length} frame keys accounted for, prompt ${prompt.length} chars`);
