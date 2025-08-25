
def test_bfcache_reload_script_present(client):
    resp = client.get('/login')
    assert 'pageshow' in resp.get_data(as_text=True)


def test_bfcache_reload_script_disabled(app, client):
    app.config['BFCACHE_RELOAD_ENABLED'] = False
    resp = client.get('/login')
    assert 'pageshow' not in resp.get_data(as_text=True)