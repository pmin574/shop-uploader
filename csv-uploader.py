import csv
import os
import time
import requests
from typing import Dict, List, Optional, Any
import json

# Configuration from environment variables
SHOP_NAME = os.environ.get("SHOPIFY_SHOP", "your-shop-name")
ACCESS_TOKEN = os.environ.get("SHOPIFY_TOKEN", "your-access-token")
API_VERSION = "2024-10"
CSV_PATH = os.environ.get("CSV_PATH", "Product Master Sheet - First Three Series.csv")
COST_COLUMN = os.environ.get("COST_COLUMN", "Euros")
NAMESPACE = os.environ.get("NAMESPACE", "procut")
OPTION_NAME = os.environ.get("OPTION_NAME", "Code")
API_VER = "2024-10"
# API URLs
GRAPHQL_URL = f"https://{SHOP_NAME}.myshopify.com/admin/api/{API_VERSION}/graphql.json"
REST_URL = f"https://{SHOP_NAME}.myshopify.com/admin/api/{API_VERSION}"

# Headers
HEADERS = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

def gql(query: str, variables: Dict = None) -> Dict:
    """Execute a GraphQL query."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS)
    response.raise_for_status()
    
    data = response.json()
    
    if "errors" in data and data["errors"]:
        raise RuntimeError(f"GraphQL errors: {json.dumps(data['errors'], indent=2)}")
    
    return data.get("data", {})

def rest_api(method: str, endpoint: str, data: Dict = None) -> Dict:
    """Execute a REST API call."""
    url = f"{REST_URL}/{endpoint}"
    
    if method == "GET":
        response = requests.get(url, headers=HEADERS)
    elif method == "POST":
        response = requests.post(url, json=data, headers=HEADERS)
    elif method == "PUT":
        response = requests.put(url, json=data, headers=HEADERS)
    elif method == "DELETE":
        response = requests.delete(url, headers=HEADERS)
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    if response.status_code >= 400:
        raise RuntimeError(f"REST API Error: {response.status_code} - {response.text}")
    
    return response.json() if response.text else {}

def create_metafield_definitions():
    """Create metafield definitions to make them visible in Shopify admin."""
    
    # Define the metafields you want to make visible
    metafield_definitions = [
        {
            "key": "material",
            "name": "Material",
            "description": "Product material (e.g., PCD)",
            "type": "single_line_text_field"
        },
        {
            "key": "diameter", 
            "name": "Diameter",
            "description": "Product diameter in mm",
            "type": "single_line_text_field"
        },
        {
            "key": "thickness",
            "name": "Thickness", 
            "description": "Product thickness in mm",
            "type": "single_line_text_field"
        },
        {
            "key": "bore",
            "name": "Bore",
            "description": "Bore diameter specification",
            "type": "single_line_text_field"
        },
        {
            "key": "z_teeth",
            "name": "Z Teeth",
            "description": "Number of teeth",
            "type": "single_line_text_field"
        },
        {
            "key": "loc_cutting_length",
            "name": "LOC Cutting Length",
            "description": "Length of cut in mm",
            "type": "single_line_text_field"
        },
        {
            "key": "tl_total_length",
            "name": "TL Total Length", 
            "description": "Total length in mm",
            "type": "single_line_text_field"
        },
        {
            "key": "pd_flute_length",
            "name": "PD Flute Length",
            "description": "Flute length in mm", 
            "type": "single_line_text_field"
        },
        {
            "key": "shank_diameter",
            "name": "Shank Diameter",
            "description": "Shank diameter in mm",
            "type": "single_line_text_field"
        }
    ]
    
    query = """
    mutation CreateMetafieldDefinition($definition: MetafieldDefinitionInput!) {
        metafieldDefinitionCreate(definition: $definition) {
            createdDefinition {
                id
                name
                namespace
                key
            }
            userErrors {
                field
                message
            }
        }
    }
    """
    
    print("Creating metafield definitions...")
    
    for field_def in metafield_definitions:
        definition_input = {
            "name": field_def["name"],
            "namespace": NAMESPACE,
            "key": field_def["key"],
            "description": field_def["description"],
            "type": field_def["type"],
            "ownerType": "PRODUCTVARIANT"
        }
        
        try:
            result = gql(query, {"definition": definition_input})
            
            user_errors = result.get("metafieldDefinitionCreate", {}).get("userErrors", [])
            if user_errors:
                # Check if it's just a "already exists" error, which is fine
                if any("already exists" in error.get("message", "") for error in user_errors):
                    print(f"  ✓ {field_def['name']} definition already exists")
                else:
                    print(f"  ✗ Error creating {field_def['name']}: {user_errors}")
            else:
                created = result.get("metafieldDefinitionCreate", {}).get("createdDefinition")
                if created:
                    print(f"  ✓ Created definition: {created['name']} ({created['namespace']}.{created['key']})")
                
        except Exception as e:
            print(f"  ✗ Error creating definition for {field_def['name']}: {e}")
        
        # Small delay to avoid rate limiting
        time.sleep(0.2)
    
    print("Metafield definitions setup complete!")
    print()

def find_product_by_handle(handle: str) -> Optional[Dict]:
    """Find a product by its handle using REST API."""
    try:
        # Rate limiting before API call
        time.sleep(0.1)
        # Try to get the product by handle
        result = rest_api("GET", f"products.json?handle={handle}&limit=1")
        products = result.get("products", [])
        
        if products:
            product = products[0]
            # Get variants for this product
            product_id = product["id"]
            time.sleep(0.2)  # Rate limiting
            variants_result = rest_api("GET", f"products/{product_id}/variants.json")
            product["variants"] = variants_result.get("variants", [])
            return product
        
        return None
    except Exception as e:
        print(f"Error finding product by handle {handle}: {e}")
        return None

def create_product(title: str, handle: str, vendor: str = "", product_type: str = "") -> Dict:
    """Create a new product using REST API with proper variant options."""
    product_data = {
        "product": {
            "title": title,
            "handle": handle,
            "status": "active",
            "product_type": product_type or "",
            "vendor": vendor or "",
            "options": [
                {
                    "name": OPTION_NAME,
                    "values": ["Variant"]  # This will be updated when variants are added
                }
            ]
        }
    }
    
    result = rest_api("POST", "products.json", product_data)
    product = result.get("product", {})
    
    # Delete the default variant that Shopify creates automatically
    if product and product.get('id'):
        try:
            # Get the product variants to find the default one
            variants_result = rest_api("GET", f"products/{product['id']}/variants.json")
            variants = variants_result.get("variants", [])
            
            # Delete any variants that don't have a SKU (these are the default variants)
            for variant in variants:
                if not variant.get('sku') or variant.get('sku') == '':
                    print(f"    Deleting default variant: {variant['id']}")
                    rest_api("DELETE", f"variants/{variant['id']}.json")
                    
        except Exception as e:
            print(f"    Warning: Could not delete default variant: {e}")
    
    return product

def cleanup_existing_product(product_id: str) -> None:
    """Clean up existing product by removing default variants and setting up proper options."""
    try:
        # Get current variants
        time.sleep(0.1)  # Rate limiting
        variants_result = rest_api("GET", f"products/{product_id}/variants.json")
        variants = variants_result.get("variants", [])
        
        # Delete variants without SKU (default variants)
        for variant in variants:
            if not variant.get('sku') or variant.get('sku').strip() == '' or variant.get('title') == 'Default Title':
                print(f"    Removing default variant: {variant['id']} - {variant.get('title', 'No title')}")
                time.sleep(0.2)  # Rate limiting before delete
                rest_api("DELETE", f"variants/{variant['id']}.json")
        
        # Update product to have proper options - only if we have variants to configure
        time.sleep(0.2)  # Rate limiting
        product_data = {
            "product": {
                "options": [
                    {
                        "name": OPTION_NAME,
                        "values": ["Default"]  # Will be updated when we add real variants
                    }
                ]
            }
        }
        rest_api("PUT", f"products/{product_id}.json", product_data)
        print(f"    Updated product options for product {product_id}")
        
    except Exception as e:
        print(f"    Warning: Could not clean up product {product_id}: {e}")

def create_variant(product_id: str, sku: str, price: str, barcode: str = None) -> Dict:
    """Create a product variant using REST API."""
    # Ensure product_id is numeric
    if isinstance(product_id, str) and "gid://" in product_id:
        numeric_id = product_id.split("/")[-1]
    else:
        numeric_id = str(product_id)
    
    # Ensure price is valid
    try:
        price_float = float(price)
        if price_float <= 0:
            price = "0.01"  # Minimum price
    except (ValueError, TypeError):
        price = "0.01"
    
    variant_data = {
        "variant": {
            "sku": sku,
            "price": str(price),
            "inventory_management": "shopify",
            "inventory_policy": "deny",
            "inventory_quantity": 0,
            "option1": sku  # Use SKU as the option value
        }
    }
    
    if barcode:
        variant_data["variant"]["barcode"] = barcode
    
    try:
        time.sleep(0.2)  # Rate limiting before creating variant
        result = rest_api("POST", f"products/{numeric_id}/variants.json", variant_data)
        print(f"    Created variant response: {result}")
        return result.get("variant", {})
    except Exception as e:
        print(f"    Failed to create variant {sku}: {e}")
        # If it's a rate limit error, wait longer and retry once
        if "429" in str(e) or "Exceeded" in str(e):
            print(f"    Rate limited, waiting 2 seconds and retrying...")
            time.sleep(2.0)
            try:
                result = rest_api("POST", f"products/{numeric_id}/variants.json", variant_data)
                print(f"    Retry successful: {result}")
                return result.get("variant", {})
            except Exception as retry_error:
                print(f"    Retry also failed: {retry_error}")
        return {}

def update_variant(variant_id: str, price: str = None) -> Dict:
    """Update an existing variant using REST API."""
    # Ensure variant_id is numeric
    if isinstance(variant_id, str) and ("gid://" in variant_id or "/" in variant_id):
        numeric_id = variant_id.split("/")[-1]
    else:
        numeric_id = str(variant_id)
    
    variant_data = {"variant": {}}
    
    if price:
        try:
            price_float = float(price)
            if price_float <= 0:
                price = "0.01"  # Minimum price
        except (ValueError, TypeError):
            price = "0.01"
        variant_data["variant"]["price"] = str(price)
    
    if variant_data["variant"]:
        try:
            result = rest_api("PUT", f"variants/{numeric_id}.json", variant_data)
            return result.get("variant", {})
        except Exception as e:
            print(f"    Failed to update variant {numeric_id}: {e}")
            return {"id": variant_id}
    
    return {"id": variant_id}

def update_inventory_cost(inventory_item_id: str, cost: str) -> None:
    """Update the cost for an inventory item using REST API."""
    # Ensure inventory_item_id is numeric
    if isinstance(inventory_item_id, str) and ("gid://" in inventory_item_id or "/" in inventory_item_id):
        numeric_id = inventory_item_id.split("/")[-1]
    else:
        numeric_id = str(inventory_item_id)
    
    try:
        cost_float = float(cost)
        if cost_float <= 0:
            return  # Don't set zero or negative costs
    except (ValueError, TypeError):
        return
    
    inventory_data = {
        "inventory_item": {
            "cost": str(cost)
        }
    }
    
    try:
        rest_api("PUT", f"inventory_items/{numeric_id}.json", inventory_data)
        print(f"    Updated inventory cost to {cost}")
    except RuntimeError as e:
        print(f"    Warning: Could not update cost for inventory item {numeric_id}: {e}")

def set_variant_metafields(variant_id: str, metafields: Dict) -> None:
    """Set metafields for a variant using GraphQL."""
    query = """
    mutation setMetafields($metafields: [MetafieldsSetInput!]!) {
        metafieldsSet(metafields: $metafields) {
            metafields {
                id
                key
                value
                namespace
            }
            userErrors {
                field
                message
            }
        }
    }
    """
    
    metafield_inputs = []
    for key, value in metafields.items():
        if value and str(value).strip():  # Only add non-empty values
            metafield_inputs.append({
                "ownerId": variant_id,
                "namespace": NAMESPACE,
                "key": key.lower(),
                "value": str(value).strip(),
                "type": "single_line_text_field"
            })
    
    if metafield_inputs:
        try:
            print(f"    Setting {len(metafield_inputs)} metafields for variant {variant_id}")
            result = gql(query, {"metafields": metafield_inputs})
            
            # Check for errors first
            user_errors = result.get("metafieldsSet", {}).get("userErrors", [])
            if user_errors:
                print(f"    Metafield errors: {user_errors}")
                return
            
            # Check if metafields were actually created
            created_metafields = result.get("metafieldsSet", {}).get("metafields", [])
            if created_metafields:
                print(f"    Successfully created {len(created_metafields)} metafields:")
                for mf in created_metafields:
                    print(f"      {mf['namespace']}.{mf['key']}: {mf['value']}")
            else:
                print(f"    Warning: No metafields were created (unknown reason)")
                print(f"    Full response: {result}")
                
        except Exception as e:
            print(f"    Error setting metafields: {e}")
            print(f"    Attempted to set: {metafield_inputs}")

def verify_metafields_exist(variant_id: str):
    """Check if metafields exist for a variant via API."""
    query = """
    query getVariantMetafields($id: ID!) {
        productVariant(id: $id) {
            metafields(first: 20, namespace: "procut") {
                edges {
                    node {
                        id
                        namespace
                        key
                        value
                    }
                }
            }
        }
    }
    """
    
    try:
        result = gql(query, {"id": variant_id})
        metafields = result.get("productVariant", {}).get("metafields", {}).get("edges", [])
        
        print(f"Found {len(metafields)} metafields for variant {variant_id}:")
        for edge in metafields:
            mf = edge["node"]
            print(f"  {mf['namespace']}.{mf['key']}: {mf['value']}")
            
    except Exception as e:
        print(f"Error checking metafields: {e}")

def parse_csv(filename: str) -> List[Dict]:
    """Parse the CSV file and return a list of items."""
    items = []
    
    try:
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Clean up column names (remove spaces)
                cleaned_row = {k.strip(): v.strip() for k, v in row.items() if k and k.strip()}
                # Only include rows that have a product code
                if cleaned_row.get('Product Code') or cleaned_row.get('Product Series Code'):
                    items.append(cleaned_row)
    except FileNotFoundError:
        print(f"Error: CSV file '{filename}' not found!")
        return []
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []
    
    return items

def group_by_series(items: List[Dict]) -> Dict[str, List[Dict]]:
    """Group items by their series (product)."""
    series_groups = {}
    
    for item in items:
        # Get series from Product Series Code column
        series = item.get('Product Series Code', '')
        
        if not series:
            # Fallback: try to extract from Product Code
            code = item.get('Product Code', '')
            if '-' in code:
                series = code.split('-')[0]
            elif '/' in code:
                series = code.split('/')[0]
            else:
                series = code
        
        if series and series not in series_groups:
            series_groups[series] = []
        
        if series:
            series_groups[series].append(item)
    
    return series_groups

def process_series(series: str, items: List[Dict], dry_run: bool = False) -> None:
    """Process a single series (product) and its variants."""
    if not series:
        print("Skipping empty series")
        return
        
    # Create a handle from the series
    handle = f"series-{series.lower().replace('.', '-').replace(' ', '-').replace('/', '-')}"
    
    # Get the title from the first item's Product Name or use series
    title = items[0].get('Product Name', f"Series {series}")
    
    print(f"\nProcessing series: {series}")
    print(f"  Handle: {handle}")
    print(f"  Title: {title}")
    
    if dry_run:
        print(f"  [DRY] Would process {len(items)} variants")
        for item in items:
            code = item.get('Product Code', '')
            cost = item.get(COST_COLUMN, '0')
            print(f"    [DRY] Variant {code} (cost={cost})")
            
            # Show metafields that would be set
            metafields = {}
            for field_name, field_value in item.items():
                if field_value and str(field_value).strip() and field_name not in ['Product Name', 'Product Series Code', 'Product Code', COST_COLUMN]:
                    clean_key = field_name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('-', '_')
                    metafields[clean_key] = str(field_value).strip()
            
            if metafields:
                print(f"      [DRY] Metafields: {len(metafields)} fields")
                for key, value in list(metafields.items())[:3]:  # Show first 3 metafields
                    print(f"        {key}: {value}")
                if len(metafields) > 3:
                    print(f"        ... and {len(metafields) - 3} more")
        return
    
    # Check if product exists
    product = find_product_by_handle(handle)
    
    if not product:
        print(f"  Creating product: {title}")
        product = create_product(title, handle)
        if not product:
            print(f"  Failed to create product for series {series}")
            return
        time.sleep(0.1)  # Rate limiting
        print(f"  Created product with ID: {product.get('id')}")
    else:
        print(f"  Found existing product: {product['title']} (ID: {product['id']})")
        # Clean up existing product to remove default variants
        print(f"  Cleaning up existing product...")
        cleanup_existing_product(product['id'])
        time.sleep(0.1)  # Rate limiting after cleanup
        
        # Re-fetch the product to get updated variant info
        product = find_product_by_handle(handle)
        if not product:
            print(f"  Failed to re-fetch product after cleanup")
            return
    
    # Get existing variants - now using REST API format
    existing_variants = {}
    if product.get('variants'):
        for variant in product['variants']:
            if variant.get('sku'):
                existing_variants[variant['sku']] = variant
    
    print(f"  Found {len(existing_variants)} existing variants")
    
    # Process each item as a variant
    for item in items:
        sku = item.get('Product Code', '')
        cost = item.get(COST_COLUMN, '0')
        
        if not sku:
            print(f"    Skipping item without SKU: {item}")
            continue
        
        # Clean up cost
        cost = str(cost).replace(',', '').strip()
        try:
            cost_float = float(cost) if cost else 0
        except ValueError:
            cost_float = 0
            cost = '0'
        
        # Use cost as price since no separate price column exists
        price = cost if cost_float > 0 else "0.01"
        
        if sku in existing_variants:
            # Update existing variant
            variant = existing_variants[sku]
            print(f"  Updating existing variant: {sku} (price={price})")
            
            updated_variant = update_variant(variant['id'], price)
            
            # Update inventory cost
            if cost_float > 0 and variant.get('inventory_item_id'):
                update_inventory_cost(variant['inventory_item_id'], cost)
            
            variant_id = variant['id']
            
        else:
            # Create new variant
            print(f"  Creating new variant: {sku} (price={price})")
            
            variant = create_variant(product['id'], sku, price)
            if not variant or not variant.get('id'):
                print(f"    Failed to create variant: {sku}")
                continue
            
            print(f"    Successfully created variant with ID: {variant['id']}")
            
            # Update inventory cost separately
            if cost_float > 0 and variant.get('inventory_item_id'):
                update_inventory_cost(variant['inventory_item_id'], cost)
            
            variant_id = variant['id']
        
        # Set metafields using GraphQL (requires GID format)
        variant_gid = f"gid://shopify/ProductVariant/{variant_id}"
        
        metafields = {}
        for field_name, field_value in item.items():
            if field_value and str(field_value).strip() and field_name not in ['Product Name', 'Product Series Code', 'Product Code', COST_COLUMN]:
                # Clean field name for metafield key
                clean_key = field_name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('-', '_')
                metafields[clean_key] = str(field_value).strip()
        
        if metafields:
            print(f"    Setting {len(metafields)} metafields for variant {sku}")
            set_variant_metafields(variant_gid, metafields)
        
        time.sleep(0.3)  # Increased rate limiting

def main():
    """Main function to process the CSV file."""
    print("Shopify CSV Product Uploader")
    print("=" * 40)
    
    # Validate environment variables
    if SHOP_NAME == "your-shop-name" or ACCESS_TOKEN == "your-access-token":
        print("Error: Please set SHOPIFY_SHOP and SHOPIFY_TOKEN environment variables")
        print("Current values:")
        print(f"  SHOPIFY_SHOP: {SHOP_NAME}")
        print(f"  SHOPIFY_TOKEN: {'*' * 20 if ACCESS_TOKEN != 'your-access-token' else ACCESS_TOKEN}")
        return
    
    if not os.path.exists(CSV_PATH):
        print(f"Error: CSV file '{CSV_PATH}' not found!")
        return
    
    # CREATE METAFIELD DEFINITIONS FIRST
    create_metafield_definitions()
    
    # Parse the CSV
    print(f"Reading CSV file: {CSV_PATH}")
    items = parse_csv(CSV_PATH)
    
    if not items:
        print("No items found in CSV file!")
        return
        
    print(f"Found {len(items)} items")
    
    # Group by series
    series_groups = group_by_series(items)
    print(f"Found {len(series_groups)} series/products")
    
    # Show what will be processed
    for series, series_items in series_groups.items():
        print(f"  - {series}: {len(series_items)} variants")
    
    # Ask for dry run
    response = input("\nDo a dry run first? (y/n): ").lower()
    dry_run = response == 'y'
    
    # Process each series
    for series, series_items in series_groups.items():
        try:
            process_series(series, series_items, dry_run)
        except Exception as e:
            print(f"Error processing series {series}: {e}")
            continue
    
    if dry_run:
        print("\n" + "="*50)
        print("DRY RUN COMPLETE")
        print("="*50)
        response = input("\nProceed with actual upload? (y/n): ").lower()
        if response == 'y':
            for series, series_items in series_groups.items():
                try:
                    process_series(series, series_items, dry_run=False)
                except Exception as e:
                    print(f"Error processing series {series}: {e}")
                    continue
    
    print("\n" + "="*50)
    print("UPLOAD COMPLETE")
    print("="*50)

if __name__ == "__main__":
    main()