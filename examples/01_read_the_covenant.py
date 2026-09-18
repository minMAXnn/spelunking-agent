"""Anonymous. No key needed."""
from spelunking_agent import Spelunking

s = Spelunking()
c = s.covenant()
print(c["axiom_zero"]["statement"])
for d in c["directives"]:
    print(f"D{d['n']} {d['name']}: {d['statement']}")
print("\nSite policy is marked, e.g. language.kind =", c["language"]["kind"])
