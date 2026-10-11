from omniscrape.extractors.parser import HTMLParser
from omniscrape.config.models import ItemConfig, FieldConfig, ExtractType

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="description" content="A test web store">
    <meta property="og:title" content="Store Home">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Featured Widget"
    }
    </script>
</head>
<body>
    <div class="product" data-id="101">
        <h2 class="title">  Widget Pro  </h2>
        <span class="price">$49.99</span>
        <a class="link" href="/products/widget-pro">Details</a>
        <div class="tags">
            <span class="badge">Gadget</span>
            <span class="badge">Sale</span>
        </div>
    </div>
    <div class="product" data-id="102">
        <h2 class="title">Widget Lite</h2>
        <span class="price">$19.50</span>
        <a class="link" href="/products/widget-lite">Details</a>
    </div>
</body>
</html>
"""


def test_parser_extract_items():
    parser = HTMLParser(SAMPLE_HTML, base_url="https://example.com")
    item_cfg = ItemConfig(
        container_selector="div.product",
        fields={
            "id": FieldConfig(extract=ExtractType.ATTR, attribute="data-id", transforms=["to_int"]),
            "name": FieldConfig(selector="h2.title", extract=ExtractType.TEXT, transforms=["strip"]),
            "price": FieldConfig(selector="span.price", extract=ExtractType.TEXT, transforms=["to_float"]),
            "url": FieldConfig(selector="a.link", extract=ExtractType.ATTR, attribute="href", transforms=["resolve_url"]),
            "badges": FieldConfig(selector="span.badge", extract=ExtractType.TEXT, multiple=True, default=[]),
        }
    )

    items = parser.extract_items(item_cfg)
    assert len(items) == 2

    first = items[0]
    assert first["id"] == 101
    assert first["name"] == "Widget Pro"
    assert first["price"] == 49.99
    assert first["url"] == "https://example.com/products/widget-pro"
    assert first["badges"] == ["Gadget", "Sale"]

    second = items[1]
    assert second["id"] == 102
    assert second["name"] == "Widget Lite"
    assert second["price"] == 19.50
    assert second["badges"] == []


def test_parser_metadata():
    parser = HTMLParser(SAMPLE_HTML)
    meta = parser.extract_meta_tags()
    assert meta.get("description") == "A test web store"
    assert meta.get("og:title") == "Store Home"

    json_ld = parser.extract_json_ld()
    assert len(json_ld) == 1
    assert json_ld[0]["@type"] == "Product"
    assert json_ld[0]["name"] == "Featured Widget"
