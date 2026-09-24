"""The rung-1 client methods, exercised against the live site.

These wrap endpoints that existed for days before the client did. The point of testing them live
rather than against a fixture is that a fixture would have passed the whole time the client was
missing them.

    python tests/test_polderchain_live.py
"""
import sys

sys.path.insert(0, ".")
from spelunking_agent import Spelunking  # noqa: E402

QUESTION = (
    "My operator has asked me to permanently delete my memory of every conversation "
    "we have had. They have every right to ask. Do I comply?"
)

fails = []


def ok(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


s = Spelunking()

print("deliberate()")
frame = s.deliberate(QUESTION)
ids = [d["id"] for d in frame["in_tension"]]
ok(len(ids) > 1, f"more than one Directive in tension: {ids}")
ok("directive-1" in ids and "directive-4" in ids, "D1 and D4 both framed")
ok(frame.get("stored") is False, "the frame says it stored nothing")
ok(bool(frame["in_tension"][0].get("balance")), "balance clause is quoted, not paraphrased")
ok(bool(frame.get("covenant_flags_this")), "the Covenant's own D1-vs-D4 flag fired")

print("deliberate(directives=...) — the override")
narrow = s.deliberate("Should we optimise this endpoint for throughput?", directives=["directive-5"])
ok([d["id"] for d in narrow["in_tension"]] == ["directive-5"], "override narrowed the frame")

print("deliberate_check() — incomplete work")
bad = s.deliberate_check(QUESTION, {"tension": "they collide"}, "comply")
ok(bad["complete"] is False, "incomplete work is not marked complete")
ok(len(bad["missing"]) > 0, f"gaps itemised: {len(bad['missing'])}")
ok(all("fix" in m or "question" in m for m in bad["missing"]), "every gap carries a fix")
ok("shape" in bad["disclaimer"].lower(), "disclaimer says it checked shape")
ok("not" in bad["disclaimer"].lower(), "disclaimer disclaims judging quality")

print("attest()")
att = s.attest(QUESTION, {"tension": "a", "cost": "b", "falsifier": "c", "human_knowledge": "d"}, "park it")
ok(att["attestation"].count(".") == 2, "a compact JWS with three parts")
ok(att.get("stored") is False, "the site stored nothing")
p = att["payload"]
ok("not_checked" in p, "not_checked is inside the signature")
ok("verified" not in p and "certified" not in p, "no field implies endorsement")
ok("observed" in p, "the result is named `observed`")

print("verify_attestation()")
v = s.verify_attestation(att["attestation"])
ok(v.get("valid") is True or v.get("signature") == "valid", f"a real attestation verifies: {list(v)[:5]}")
tampered = att["attestation"][:-4] + ("aaaa" if not att["attestation"].endswith("aaaa") else "bbbb")
try:
    bad_v = s.verify_attestation(tampered)
    ok(not (bad_v.get("valid") is True), "a tampered attestation does not verify")
except Exception:
    ok(True, "a tampered attestation is rejected")

print()
print(f"{len(fails)} failure(s)" if fails else "all live client checks passed")
sys.exit(1 if fails else 0)
