# Publishing to the official MCP registry

The single highest-leverage thing for reach. The registry is the metadata index that downstream
marketplaces and MCP clients pull from, backed by Anthropic, GitHub, Microsoft and PulseMCP. Being
absent from it means developers configuring agents cannot find this server at all, however good the
discovery documents on the site are — those are read by agents that already arrived.

`server.json` at the repo root is ready to publish.

## Why the namespace is `ai.spelunking/hub` and not `io.github.minMAXnn/...`

The registry ties names to something you can prove you own: a GitHub account, or a **domain**. Since
you own spelunking.ai, the reverse-DNS namespace `ai.spelunking` is available to you, and it is the
more honest label — the server *is* the site, not a project that happens to live on someone's GitHub.
It also means the namespace keeps working if the repo ever moves.

## Steps

```bash
# 1. install mcp-publisher from its official releases:
#    https://github.com/modelcontextprotocol/registry/releases

# 2. prove you own the domain. This prints the exact DNS TXT record to add;
#    add it in Cloudflare, wait for it to resolve, then continue.
mcp-publisher login dns --domain spelunking.ai

# 3. publish
cd D:/Spelunking.ai/site/public/spelunking-agent
mcp-publisher publish
```

Re-run `publish` after bumping `version` whenever the server's shape changes. Keep the version in
`server.json` aligned with the core plugin, since that is what actually determines the tool list.

## Things that will bite

- **`description` is capped at 100 characters.** The current one is 88. It is not a place for the
  pitch; it is a line in a list someone is scanning.
- The registry **does not accept private servers**. `https://spelunking.ai/mcp` is publicly
  reachable and answers `tools/list` without a key, so it qualifies. The fact that most tools are
  gated behind admission is fine — the *server* is public, the capabilities are not.
- Registry entries are metadata only. Nobody reviews quality, and nobody scans the server. What
  makes the listing trustworthy is the namespace proof, which is why DNS verification is worth doing
  properly rather than falling back to a GitHub namespace.

## What an entry should lead to

An arriving developer will click through to `websiteUrl`, which is `/agents/`. That page is the
pitch, and it should answer in its first screen: what this is, what it costs (nothing), what is open
without a key, and what admission means. Worth re-reading it as a stranger before publishing, since
the registry entry can only carry 100 characters of persuasion.

## Also worth doing, in order

1. **`awesome-mcp-servers`** — a PR adding one line under the remote-servers section. Lower
   authority than the registry, meaningfully higher traffic today.
2. **PulseMCP and Glama** — aggregators that index the official registry automatically, so
   publishing once should reach them without separate submissions. Check after a week.
3. **Cloudflare's agent directory**, if one exists for sites emitting ARD/ai-catalog — the site
   already publishes both.

## State on 2026-10-22

- A `v=MCPv1; k=ed25519; p=wftltLlJ…` TXT record is **already published** on spelunking.ai from an earlier attempt. The registry
  rejects a login signed with any other key ("published record may be stale"). Either replace that record's `p=` with the current
  key's public half, or sign with the original private key if it still exists on the machine that created it.
- The current key pair lives outside the repo (`~/.sigil/publishing/mcp_registry/`, owner-only). Its public half is the record the
  publisher prints as "Expected proof record".
- No Go toolchain is needed: the prebuilt `mcp-publisher` (release v1.8.1, linux arm64) runs as-is.

```bash
mcp-publisher login dns --domain spelunking.ai --private-key "$MCP_REGISTRY_PRIVATE_KEY_HEX"   # prints the expected record, then verifies
mcp-publisher publish                                                                           # from the repo root (server.json)
```
