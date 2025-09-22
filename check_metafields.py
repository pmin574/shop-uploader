import os
import requests

# Configuration
SHOP_NAME = os.environ.get("SHOPIFY_SHOP", "your-shop-name")
ACCESS_TOKEN = os.environ.get("SHOPIFY_TOKEN", "your-access-token")
API_VERSION = "2024-10"

# GraphQL URL
GRAPHQL_URL = f"https://{SHOP_NAME}.myshopify.com/admin/api/{API_VERSION}/graphql.json"

# Headers
HEADERS = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

def check_variant_metafields():
    """Check metafields for a specific variant."""
    
    # GraphQL query to find a variant and its metafields
    query = """
    query {
      productVariants(first: 1, query: "sku:8L.1001-300X3.2Z72") {
        edges {
          node {
            id
            sku
            metafields(namespace: "procut", first: 10) {
              edges {
                node {
                  namespace
                  key
                  value
                  type
                }
              }
            }
          }
        }
      }
    }
    """
    
    try:
        response = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
        response.raise_for_status()
        
        data = response.json()
        
        if "errors" in data:
            print(f"GraphQL Errors: {data['errors']}")
            return
        
        variants = data.get("data", {}).get("productVariants", {}).get("edges", [])
        
        if not variants:
            print("No variants found with that SKU")
            return
        
        variant = variants[0]["node"]
        metafields = variant.get("metafields", {}).get("edges", [])
        
        print(f"Variant: {variant['sku']} (ID: {variant['id']})")
        print(f"Found {len(metafields)} metafields:")
        
        if metafields:
            for metafield in metafields:
                node = metafield["node"]
                print(f"  {node['namespace']}.{node['key']}: {node['value']} ({node['type']})")
        else:
            print("  No metafields found!")
            
    except Exception as e:
        print(f"Error: {e}")

def list_all_variants_with_metafields():
    """List several variants to check metafields."""
    
    query = """
    query {
      productVariants(first: 5) {
        edges {
          node {
            id
            sku
            metafields(namespace: "procut", first: 5) {
              edges {
                node {
                  namespace
                  key
                  value
                }
              }
            }
          }
        }
      }
    }
    """
    
    try:
        response = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
        response.raise_for_status()
        
        data = response.json()
        variants = data.get("data", {}).get("productVariants", {}).get("edges", [])
        
        print(f"\nChecking first 5 variants:")
        print("="*50)
        
        for variant_edge in variants:
            variant = variant_edge["node"]
            metafields = variant.get("metafields", {}).get("edges", [])
            
            print(f"\nVariant: {variant.get('sku', 'No SKU')}")
            if metafields:
                print(f"  Metafields ({len(metafields)}):")
                for mf in metafields:
                    node = mf["node"]
                    print(f"    {node['key']}: {node['value']}")
            else:
                print("  No metafields found")
                
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("Shopify Metafield Checker")
    print("=" * 40)
    
    if SHOP_NAME == "your-shop-name":
        print("Please set your environment variables first!")
        return
    
    print("1. Checking specific variant metafields...")
    check_variant_metafields()
    
    print("\n2. Checking multiple variants...")
    list_all_variants_with_metafields()

if __name__ == "__main__":
    main()