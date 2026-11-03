from eco_sentinel.utils.helpers import slugify


def test_slugify():
    assert slugify("Hello World!") == "hello-world"
    assert slugify("  Eco Sentinel Africa  ") == "eco-sentinel-africa"


def test_slugify_compat():
    """Compat — l'ancien import doit toujours fonctionner."""
    from meta_ai_dev.utils.helpers import slugify as compat_slugify

    assert compat_slugify("Hello World!") == "hello-world"
