## What changed

<!-- one change per PR; say what and why in two or three sentences -->

## Who is opening this

- [ ] a person
- [ ] an agent — model: `…` · a person reviewed this before I opened it: yes / no

## Checks

- [ ] `python -m pytest -q` passes offline
- [ ] no new dependency in the client (examples may declare their own)
- [ ] no key, no gated data, nothing read from the hub
- [ ] the client still sends keys only as `Authorization: Bearer`
