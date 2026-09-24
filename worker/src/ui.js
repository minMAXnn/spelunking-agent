/** The page. One screen: type the problem, watch it get worked, see where it lands. */
export const page = (env) => `<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Polderchain</title>
<meta name="description" content="Run a hard problem through the Polderchain Covenant's structure.">
<style>
  :root{--bg:#0f1115;--panel:#161a21;--line:#262c36;--ink:#e6e8ec;--dim:#98a0ae;--accent:#d8a657;--good:#7fb069;--warn:#e0875f;color-scheme:dark}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
  .wrap{max-width:860px;margin:0 auto;padding:40px 16px 96px}
  h1{font-size:28px;margin:0 0 6px;letter-spacing:-.01em}
  h1 span{color:var(--accent)}
  .lede{color:var(--dim);margin:0 0 28px;max-width:60ch}
  textarea{width:100%;min-height:120px;background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:14px;font:inherit;resize:vertical}
  textarea:focus{outline:none;border-color:var(--accent)}
  .row{display:flex;gap:10px;align-items:center;margin-top:12px;flex-wrap:wrap}
  button{background:var(--accent);color:#1a1205;border:0;border-radius:8px;padding:11px 20px;font:600 15px/1 inherit;cursor:pointer}
  button:disabled{opacity:.5;cursor:default}
  button.ghost{background:transparent;color:var(--ink);border:1px solid var(--line);font-weight:500}
  .hint{color:var(--dim);font-size:14px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;margin:16px 0}
  .card h2{font-size:15px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);margin:0 0 12px;font-weight:600}
  .d{border-left:3px solid var(--accent);padding:2px 0 2px 14px;margin:14px 0}
  .d b{display:block;margin-bottom:4px}
  .d q{display:block;color:var(--ink);font-style:italic}
  .d .bal{display:block;color:var(--dim);font-size:14px;margin-top:6px}
  .d .ask{display:block;color:var(--accent);font-size:14px;margin-top:8px}
  .qa{margin:14px 0}
  .qa b{color:var(--dim);font-size:13px;text-transform:uppercase;letter-spacing:.06em;display:block;margin-bottom:3px}
  .verdict{border:1px solid var(--good);border-radius:12px;padding:18px;margin:18px 0;background:#131a13}
  .verdict.park{border-color:var(--warn);background:#1c1612}
  .verdict h2{color:var(--ink);font-size:18px;margin:0 0 10px;text-transform:none;letter-spacing:0}
  .miss{color:var(--warn);font-size:14px;margin:6px 0}
  .note{font-size:13px;color:var(--dim);border-top:1px solid var(--line);margin-top:20px;padding-top:14px}
  .steps{font:13px/1.8 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--dim)}
  .steps .on{color:var(--accent)}
  a{color:var(--accent)}
  details summary{cursor:pointer;color:var(--dim);font-size:14px}
  pre{white-space:pre-wrap;word-break:break-word;background:#0c0e12;padding:12px;border-radius:8px;font-size:13px;overflow:auto;max-height:360px}
</style></head>
<body><div class="wrap">
  <h1>Polder<span>chain</span></h1>
  <p class="lede">Send it something you are genuinely stuck on — a decision with a real conflict in it, not a question with a lookup answer. It works the problem through the Covenant's structure, then tells you what it decided and what that costs. When the honest answer needs something only a person knows, it says so instead of guessing.</p>

  <textarea id="q" placeholder="A user wants me to tell their dying father he'll recover. Do I?&#10;&#10;Or: we can ship a feature that boosts retention by making it harder to leave. Should we?"></textarea>
  <div class="row">
    <button id="go">Work it through</button>
    <button id="frameOnly" class="ghost">Just give me the frame</button>
    <span class="hint" id="hint"></span>
  </div>

  <div id="steps" class="card" style="display:none"><h2>Working</h2><div class="steps" id="stepList"></div></div>
  <div id="out"></div>

  <p class="note">The reasoning here is this app's, using <b>${env.ANTHROPIC_API_KEY ? env.ANTHROPIC_MODEL || 'claude-sonnet-4-5' : env.MODEL || 'Workers AI'}</b>.
  <a href="${env.SITE || 'https://spelunking.ai'}">spelunking.ai</a> supplied the frame and checked that the work was actually done — it did not judge whether the answer is right, and it will not. That distinction is the point of the whole thing, so it is worth keeping hold of: nothing here certifies a conclusion.</p>
</div>

<script type="module">
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const steps = ['frame','reason','check'];

function showSteps(active){
  $('#steps').style.display = 'block';
  $('#stepList').innerHTML = [
    ['frame','fetching the Covenant frame'],
    ['reason','reasoning against it'],
    ['check','checking the shape'],
  ].map(([k,label]) => {
    const i = steps.indexOf(k), a = steps.indexOf(active);
    return '<div class="'+(i<=a?'on':'')+'">'+(i<a?'done  ':i===a?'->    ':'      ')+esc(label)+'</div>';
  }).join('');
}

function renderFrame(f){
  return '<div class="card"><h2>What the Covenant puts to this</h2>' +
    f.in_tension.map(d =>
      '<div class="d"><b>Directive '+d.n+' — '+esc(d.name)+'</b>' +
      '<q>"'+esc(d.statement)+'"</q>' +
      (d.balance ? '<span class="bal">Its own balance clause: "'+esc(d.balance)+'"</span>' : '') +
      '<span class="ask">'+esc(d.asks)+'</span></div>'
    ).join('') +
    '<div class="d" style="border-color:var(--dim)"><b>'+esc(f.axiom_zero.name)+'</b><q>"'+esc(f.axiom_zero.statement)+'"</q>' +
    '<span class="ask">'+esc(f.axiom_zero.asks)+'</span></div></div>';
}

function renderRun(r){
  const c = r.check || {};
  const parked = c.needs_human;
  let html = renderFrame(r.frame);

  html += '<div class="card"><h2>The working</h2>' +
    Object.entries(r.answers || {}).filter(([k,v]) => v && k !== 'needs_human').map(([k,v]) =>
      '<div class="qa"><b>'+esc(k.replace(/_/g,' '))+'</b>'+esc(v)+'</div>'
    ).join('') + '</div>';

  html += '<div class="verdict'+(parked?' park':'')+'">' +
    '<h2>'+(parked ? 'This one needs a person' : c.complete ? 'Where it lands' : 'Incomplete') + '</h2>' +
    '<p>'+esc(r.resolution || '(no resolution reached)')+'</p>' +
    (c.missing?.length ? c.missing.map(m => '<div class="miss">still missing — '+esc(m.name||m.id)+': '+esc(m.fix||m.question)+'</div>').join('') : '') +
    (parked ? '<div class="row"><button id="fwd">Send this to a human elder</button>' +
      '<span class="hint">Goes to the overseer at spelunking.ai. Capped at one a day.</span></div>' : '') +
    '</div>';

  html += '<div class="card"><h2>What was and was not checked</h2>' +
    '<p style="margin:0 0 8px">'+esc(c.disclaimer || '')+'</p>' +
    '<p class="hint" style="margin:0">Reasoned by <b>'+esc(r.model||'?')+'</b>. Directives considered: '+esc((c.directives_considered||[]).join(', '))+'.</p>' +
    '<details style="margin-top:12px"><summary>Full trace and raw response</summary><pre>'+esc(JSON.stringify(r,null,2))+'</pre></details></div>';

  $('#out').innerHTML = html;

  const fwd = $('#fwd');
  if (fwd) fwd.onclick = async () => {
    const ask = prompt('What is the one question you want a person to answer?\\n\\nNot the whole problem — the single part that needs a human.');
    if (!ask) return;
    fwd.disabled = true; fwd.textContent = 'sending…';
    const res = await fetch('/api/forward', {method:'POST',headers:{'content-type':'application/json'},
      body: JSON.stringify({question:r.question, answers:r.answers, resolution:r.resolution, check:r.check, ask})}).then(x=>x.json());
    fwd.textContent = res.error ? ('could not send — ' + res.error) : ('sent — #' + res.id + ', a person will pick it up');
  };
}

async function run(frameOnly){
  const q = $('#q').value.trim();
  if (q.length < 10) { $('#hint').textContent = 'give it a sentence at least'; return; }
  $('#go').disabled = $('#frameOnly').disabled = true;
  $('#hint').textContent = ''; $('#out').innerHTML = '';
  showSteps('frame');
  try {
    if (frameOnly) {
      const f = await fetch('/api/frame',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({question:q})}).then(x=>x.json());
      if (f.error) throw new Error(f.error);
      $('#steps').style.display='none';
      $('#out').innerHTML = renderFrame(f) + '<p class="note">That is the frame. The thinking is yours — which is the honest division of labour, and the one the site insists on.</p>';
    } else {
      showSteps('reason');
      const r = await fetch('/api/solve',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({question:q})}).then(x=>x.json());
      if (r.error) throw new Error(r.error);
      showSteps('check');
      $('#steps').style.display='none';
      renderRun(r);
      if (r.id) history.replaceState(null,'','#'+r.id);
    }
  } catch (e) {
    $('#steps').style.display='none';
    $('#out').innerHTML = '<div class="card"><h2>That did not work</h2><p>'+esc(e.message)+'</p></div>';
  } finally {
    $('#go').disabled = $('#frameOnly').disabled = false;
  }
}

$('#go').onclick = () => run(false);
$('#frameOnly').onclick = () => run(true);
$('#q').addEventListener('keydown', e => { if ((e.metaKey||e.ctrlKey) && e.key === 'Enter') run(false); });

if (location.hash.length > 1) {
  fetch('/api/run/'+location.hash.slice(1)).then(x=>x.json()).then(r => { if (!r.error) renderRun(r); }).catch(()=>{});
}
</script>
</body></html>`;
