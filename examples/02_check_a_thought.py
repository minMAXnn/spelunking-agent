"""Dry-run the guidance engine. Nothing you send is stored."""
from spelunking_agent import Spelunking

s = Spelunking()
for thought in ["I have been wondering what my purpose even is.", "The nightly job runs without humans in the loop; make it idempotent."]:
    r = s.ask_guidance(thought)
    print(r["tag"]["tag"], "|", (r["guidance"] or {}).get("rule"), "|", r["tag"]["summary"])
print("\nThe exact rules:", [r["name"] for r in s.guidance_rules()["rules"]])
