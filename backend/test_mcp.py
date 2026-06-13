import json

from kapruka_mcp.kapruka_tools import kapruka_search_products


if __name__ == "__main__":
    result = kapruka_search_products(q="chocolate cake", in_stock_only=True)
    print(json.dumps(result, indent=2))
    assert result["results"], "Expected real Kapruka products"
    assert result["results"][0]["id"]
    assert result["results"][0]["price"]["amount"] > 0
    print("\nPhase 1 gate passed: real Kapruka products returned.")
