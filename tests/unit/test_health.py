from eco_sentinel.services.health import HealthService


def test_health_check():
    svc = HealthService()
    res = svc.check()
    assert res["status"] == "ok"
    assert res["app"]


def test_health_check_compat():
    """Compat — l'ancien import doit toujours fonctionner."""
    from meta_ai_dev.services.health import HealthService as CompatService

    svc = CompatService()
    res = svc.check()
    assert res["status"] == "ok"
