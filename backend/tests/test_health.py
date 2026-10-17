async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["db"] is True


async def test_meta_reports_offline_capabilities(client):
    r = await client.get("/api/meta")
    body = r.json()
    assert body["live_available"] is False
    assert body["llm_provider"] == "none"
