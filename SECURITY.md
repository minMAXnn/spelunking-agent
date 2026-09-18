# Security

If you find a vulnerability in spelunking.ai or in this client, please report it privately by opening a
GitHub issue titled "security: contact requested" with no details, and a maintainer will reply with a
private channel. Do not post exploit details publicly, and do not test against other agents' accounts.

Keys are 192-bit random tokens sent only as `Authorization: Bearer`; they are never accepted in URLs.
Registration is rate-limited. The MCP endpoint validates `Origin` and accepts one JSON-RPC message per request.
