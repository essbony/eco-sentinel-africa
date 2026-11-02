from meta_ai_dev.utils.helpers import slugify


def test_slugify():
    assert slugify("Hello World!") == "hello-world"
    assert slugify("  Meta AI Dev  ") == "meta-ai-dev"
