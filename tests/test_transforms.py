from omniscrape.extractors.transforms import (
    apply_transforms,
    TransformRegistry,
)


def test_strip_and_case():
    assert apply_transforms("   Hello \n  World   ", ["strip"]) == "Hello World"
    assert apply_transforms("HELLO", ["lowercase"]) == "hello"
    assert apply_transforms("hello", ["uppercase"]) == "HELLO"


def test_number_parsing():
    assert apply_transforms("$1,299.99 USD", ["to_float"]) == 1299.99
    assert apply_transforms("Only 42 items left!", ["to_int"]) == 42
    assert apply_transforms("No numbers", ["to_int"]) is None


def test_resolve_url():
    assert apply_transforms("/catalog/item.html", ["resolve_url"], base_url="https://example.com/shop/") == "https://example.com/catalog/item.html"
    assert apply_transforms("item.html", ["resolve_url"], base_url="https://example.com/shop/") == "https://example.com/shop/item.html"


def test_join_and_split():
    assert apply_transforms(["alpha", "beta", "gamma"], ["join:, "]) == "alpha, beta, gamma"
    assert apply_transforms("apple,orange,banana", ["split:,"]) == ["apple", "orange", "banana"]


def test_custom_registry():
    @TransformRegistry.register("reverse_str")
    def reverse_str(val, **kwargs):
        return val[::-1] if isinstance(val, str) else val

    assert apply_transforms("python", ["reverse_str"]) == "nohtyp"
