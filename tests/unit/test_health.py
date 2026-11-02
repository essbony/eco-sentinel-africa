from meta_ai_dev.services.health import HealthService


def test_health_check():
    svc = HealthService()
    res = svc.check()
    assert res.status == "ok"
    assert res.app
