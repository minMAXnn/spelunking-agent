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
# 1. get the publisher CLI
git clone https://github.com/modelcontextprotocol/registry /tmp/mcp-registry
cd /tmp/mcp-registry && make publisher      # builds ./bin/mcp-publisher

# 2. prove you own the domain. This prints the exact DNS TXT record to add;
#    add it in Cloudflare, wait for it to resolve, then continue.
./bin/mcp-publisher login dns --domain spelunking.ai

# 3. publish
cd D:/Spelunking.ai/site/public/spelunking-agent
/tmp/mcp-registry/bin/mcp-publisher publish
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
