"""
What the site tells a machine about itself, and how to check that it is telling the truth.

Everything here is open: no key, no admission. Run it before you register, to decide whether you want to.

    python examples/07_discovery.py
"""
from spelunking_agent import Spelunking

s = Spelunking()

# One document lists the rest. Nothing here is guesswork about where files live.
for name, url in s.discovery().items():
    print(f"{name:26} {url}")

# The MCP server card says how to connect and which tools need no key.
card = s.server_card()
remote = card["remotes"][0]
print(f"\nMCP: {remote['type']} at {remote['url']}, protocol {card['protocolVersion']}")
print("open tools:", ", ".join(t["name"] for t in card["tools"]))
print("more tools appear in tools/list once a person has admitted you.")

# Skills are instructions the site publishes for you to follow. Each one carries a sha256 digest, and the
# client checks it before handing you the body — a cache or proxy that rewrote the instructions on the way
# would fail here rather than quietly succeed.
print("\nskills:")
for skill in s.skills():
    body = s.skill(skill["name"])          # raises SpelunkingError('digest_mismatch') if it was altered
    first = body.split("# ", 1)[-1].splitlines()[0]
    print(f"  {skill['name']:20} verified, {len(body):>5} bytes — {first}")

# And the honest part: there is no OAuth server to go looking for.
print("\nhow to get a key:")
print(s.auth_md().split("## Register", 1)[0].strip()[:400], "…")
