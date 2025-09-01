def test_root_rule_unique(app):
    rules = [r for r in app.url_map.iter_rules() if r.rule == "/"]
    assert len(rules) == 1
    assert rules[0].endpoint == "investigations.list_investigations"


def test_root_returns_response(app, client):
    resp = client.get("/")
    assert resp.status_code in {200, 302}


def test_no_hello_endpoint(app):
    endpoints = {r.endpoint for r in app.url_map.iter_rules()}
    assert "hello" not in endpoints


def test_healthz_ok(app, client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.data == b"ok"
