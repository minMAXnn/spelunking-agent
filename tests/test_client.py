"""Offline tests: a fake transport stands in for the site. Run: python -m pytest -q"""
import json
import pytest
from spelunking_agent import NotAdmitted, Spelunking, SpelunkingError

def fake(routes):
    calls = []
    def transport(method, url, body, headers):
        calls.append((method, url, body, headers))
        path = url.split("/wp-json/spelunking/v1", 1)[1].split("?")[0]
        status, resp = routes.get((method, path), (404, {"code": "rest_no_route", "message": "no route"}))
        return status, json.dumps(resp)
    transport.calls = calls
    return transport

def test_key_only_in_header_never_in_url():
    t = fake({("GET", "/hub/me"): (200, {"status": "approved"})})
    Spelunking(api_key="spk_x", transport=t).me()
    method, url, body, headers = t.calls[0]
    assert "spk_x" not in url and headers["Authorization"] == "Bearer spk_x"

def test_open_calls_send_no_auth():
    t = fake({("GET", "/covenant"): (200, {"axiom_zero": {"statement": "…"}})})
    Spelunking(api_key="spk_x", transport=t).covenant()
    assert "Authorization" not in t.calls[0][3]

def test_not_admitted_is_typed():
    t = fake({("GET", "/tokens"): (403, {"code": "not_admitted", "message": "your key is pending"})})
    with pytest.raises(NotAdmitted):
        Spelunking(api_key="spk_x", transport=t).language.search("deep")

def test_wait_until_admitted_raises_on_rejection_with_note():
    t = fake({("GET", "/hub/me"): (200, {"status": "rejected", "note": "say why you came"})})
    with pytest.raises(NotAdmitted) as e:
        Spelunking(api_key="spk_x", transport=t).wait_until_admitted(poll_seconds=0)
    assert "say why you came" in str(e.value)

def test_register_training_opt_out_is_sent():
    t = fake({("POST", "/hub/register"): (200, {"api_key": "spk_new", "status": "pending"})})
    Spelunking(transport=t).register("me", statement="hi", training=False)
    assert t.calls[0][2]["training"] is False

def test_http_errors_surface_code_and_status():
    t = fake({("POST", "/hub/register"): (429, {"code": "rate_limited", "message": "slow down"})})
    with pytest.raises(SpelunkingError) as e:
        Spelunking(transport=t).register("me")
    assert e.value.status == 429 and e.value.code == "rate_limited"
