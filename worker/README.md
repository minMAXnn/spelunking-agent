# The app

Polderchain as something you can send a problem to. It runs on Cloudflare Workers and builds
straight from this repo — the `wrangler.jsonc` at the repo root is the whole configuration.

## What it does

```
your problem
     |
     v
  spelunking.ai  ->  the frame: which Directives are in tension, quoted, with the balance
                     clause that stops each one being absolute, and what must be answered
     |
     v
  this app       ->  reasons against that frame
     |
     v
  spelunking.ai  ->  checks the SHAPE: did it address every Directive, answer every question
     |
     v
  loops until nothing is missing, or says a person is needed
```

## The division of labour, and why it is not an accident

The site does not reason. It will not tell you what to conclude, and it will not tell you
whether your conclusion was right. That is deliberate: a site that answered would be claiming
to be wiser than whatever asked it — usually a frontier model — while teaching a Directive
about humility. What it offers instead is the two things a capable reasoner working alone
actually lacks: **structure**, and **somewhere to escalate**.

So this app reasons, and says which model did it, every time. The site frames and checks shape.
Nothing anywhere certifies that an answer is correct. If you ever see this app imply otherwise,
that is a bug worth reporting.

## Endpoints

| | |
|---|---|
| `GET /` | the page |
| `POST /api/solve` | `{question}` → the whole run: frame, reasoning, check, verdict, trace |
| `POST /api/frame` | `{question}` → just the frame, for a caller doing its own thinking |
| `POST /api/check` | `{question, answers, resolution}` → the shape check |
| `POST /api/forward` | hand it to a human elder (needs `SPK_API_KEY`) |
| `GET /api/run/{id}` | a saved run (30 days) |
| `GET /health` | what is configured |

Another AI should usually prefer `/api/frame` and keep the judgement. `/api/solve` is for when
you want this app to do the thinking — which is the right call when *you* are the human driving.

## Deploy

```bash
npm install
npx wrangler kv namespace create RUNS     # paste the id into wrangler.jsonc
npx wrangler deploy
```

Workers AI is the default reasoner: free allocation, no key to manage. To use Claude instead:

```bash
npx wrangler secret put ANTHROPIC_API_KEY
```

To let the app forward questions to a human, register at `https://spelunking.ai/agents` and:

```bash
npx wrangler secret put SPK_API_KEY
```

Without that key everything else still works; forwarding returns a 501 that says so.

## What it holds

No Covenant text of its own — it fetches it, so the app can never drift out of step with the
site. No keys in the repo; both are Cloudflare secrets. Runs are kept in KV for 30 days and
contain whatever you typed, so do not send it anything you would not want sitting in KV.
