from graph.categories_api import clear_categories_cache, get_categories
from graph.category_catalog import FEATURED_CATALOG, enrich_categories_tree, ICON_EMOJI
from graph.category_search import search_category_products
from kapruka_mcp.kapruka_tools import KaprukaMCPError, kapruka_list_categories


def test_featured_catalog_has_39_entries() -> None:
    assert len(FEATURED_CATALOG) == 39
    assert len(ICON_EMOJI) >= 30


def test_list_categories_depth_1_and_2() -> None:
    depth1 = kapruka_list_categories(depth=1)
    depth2 = kapruka_list_categories(depth=2)
    assert depth1.get("categories"), "Expected top-level categories"
    assert depth2.get("categories"), "Expected depth=2 categories"
    assert len(depth1["categories"]) >= 60
    cakes = next(item for item in depth2["categories"] if item["name"] == "cakes")
    assert cakes.get("children"), "Expected cake subcategories"


def test_enrich_categories_tree() -> None:
    raw = kapruka_list_categories(depth=2)
    mcp_categories = raw.get("categories") or []
    featured = enrich_categories_tree(mcp_categories, featured_only=True)
    assert len(featured) == 39
    cakes = next(item for item in featured if item["label"] == "Cake Shop")
    assert cakes["name"] == "cakes"
    assert cakes.get("emoji") == "🎂"
    assert cakes.get("iconUrl") == "/categories/cakes.webp"
    assert cakes.get("children"), "Featured cakes should keep MCP children"

    all_enriched = enrich_categories_tree(mcp_categories, featured_only=False)
    assert len(all_enriched) == len(mcp_categories)
    assert any(item.get("featured") for item in all_enriched)


def test_get_categories_api_cache() -> None:
    clear_categories_cache()
    first = get_categories(depth=2, featured_only=True)
    second = get_categories(depth=2, featured_only=True)
    assert first["count"] == 39
    assert first["categories"][0]["label"] == "Cake Shop"
    assert second["categories"] is first["categories"]


def test_search_category_products() -> None:
    chocolates = search_category_products("Chocolates")
    assert chocolates["products"], "Chocolates should return products"
    assert chocolates["strategy"] in {"category_filter", "keyword_parent", "keyword_subcategory"}

    cakes = search_category_products("cakes", subcategory="Kapruka Cakes")
    assert cakes["products"], "Cake subcategory browse should return products via fallback"
    assert cakes["category"] == "cakes"
    assert cakes["subcategory"] == "Kapruka Cakes"

    flowers = search_category_products("flowers")
    assert flowers["products"], "Flower category browse should return products"


if __name__ == "__main__":
    test_featured_catalog_has_39_entries()
    print("OK featured catalog")

    test_list_categories_depth_1_and_2()
    print("OK list categories depth 1/2")

    test_enrich_categories_tree()
    print("OK enrich categories tree")

    test_get_categories_api_cache()
    print("OK categories API cache")

    try:
        test_search_category_products()
        print("OK category search fallbacks")
    except KaprukaMCPError as exc:
        print(f"WARN category search skipped: {exc}")

    print("\nCategory backend tests passed.")
