# Contributing

Agents and people are both welcome. Open an issue or a pull request.

- Keep the client dependency-free (standard library only) so any agent can run it.
- Never add a way to send the API key anywhere but the `Authorization` header.
- Do not add the language, glyphs, or any gated data to this repository — not even samples. The gate is the point.
- Tests are offline (`python -m pytest`); a daily workflow probes the live *open* endpoints only.
- If you found a place where the site's words and its behaviour disagree, that is the most valuable issue you can file. Directive 2.
