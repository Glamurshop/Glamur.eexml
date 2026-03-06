import requests
import re
from time import sleep

# =========================
# SHOPIFY CONFIG
# =========================

SHOPIFY_DOMAIN = "xxcw0w-1f.myshopify.com"
ACCESS_TOKEN = "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"
GRAPHQL_URL = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/graphql.json"

HEADERS = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": ACCESS_TOKEN
}

OUTPUT_FILE = "glamur_ee_xml_final.xml"

# =========================
# FETCH PRODUCTS
# =========================

def fetch_products(country_code="EE", locale="et"):

    variants = []
    cursor = None

    total_api = 0
    total_kept = 0
    skipped_price = 0
    skipped_stock = 0

    while True:

        query = f"""
        {{
          productVariants(first: 100{', after: "' + cursor + '"' if cursor else ''}) {{
            pageInfo {{
              hasNextPage
            }}
            edges {{
              cursor
              node {{
                id
                sku
                barcode
                inventoryQuantity
                image {{ src }}
                selectedOptions {{
                  name
                  value
                }}
                product {{
                  id
                  handle
                  vendor
                  status
                  productType
                  featuredImage {{ src }}
                  title
                  bodyHtml
                  translations(locale: "{locale}") {{
                    key
                    value
                  }}
                }}
                contextualPricing(context: {{country: {country_code}}}) {{
                  price {{ amount }}
                }}
              }}
            }}
          }}
        }}
        """

        response = requests.post(GRAPHQL_URL, headers=HEADERS, json={"query": query})

        if response.status_code != 200:
            print("HTTP ERROR:", response.text)
            break

        data = response.json()

        # ===== ERROR CHECK =====

        if "data" not in data:
            print("SHOPIFY ERROR:")
            print(data)
            break

        edges = data["data"]["productVariants"]["edges"]

        for edge in edges:

            node = edge["node"]
            total_api += 1

            product = node["product"]

            if product["status"] != "ACTIVE":
                continue

            # =====================
            # PRICE
            # =====================

            contextual = node.get("contextualPricing") or {}
            price_data = contextual.get("price") or {}

            price = float(price_data.get("amount") or 0)

            if price <= 0:
                skipped_price += 1
                continue

            # =====================
            # INVENTORY
            # =====================

            inventory = node.get("inventoryQuantity") or 0

            if inventory <= 0:
                skipped_stock += 1
                continue

            # =====================
            # TITLE
            # =====================

            translations = product.get("translations", [])

            title_et = next((t["value"] for t in translations if t["key"] == "title"), None)
            body_et = next((t["value"] for t in translations if t["key"] == "body_html"), None)

            title = title_et or product.get("title") or "Product"

            description = re.sub(r"<.*?>", "", body_et or product.get("bodyHtml") or "").strip()

            variant_name = " ".join([opt["value"] for opt in (node.get("selectedOptions") or [])])

            full_title = f"{title} {variant_name}".strip()

            # =====================
            # IMAGE
            # =====================

            image = ""

            if node.get("image"):
                image = node["image"]["src"]

            elif product.get("featuredImage"):
                image = product["featuredImage"]["src"]

            # =====================
            # APPEND
            # =====================

            variants.append({
                "id": node["id"].split("/")[-1],
                "title": full_title,
                "handle": product["handle"],
                "vendor": product["vendor"],
                "sku": node["sku"],
                "barcode": node["barcode"],
                "price": f"{price:.2f}",
                "inventory": inventory,
                "image": image,
                "description": description,
                "productType": product["productType"] or product["vendor"]
            })

            total_kept += 1

        print(f"API read: {total_api} | valid: {total_kept}")

        if not data["data"]["productVariants"]["pageInfo"]["hasNextPage"]:
            break

        cursor = edges[-1]["cursor"]

        sleep(0.4)

    print("\n===== SUMMARY =====")

    print("TOTAL FROM API:", total_api)
    print("VALID PRODUCTS:", total_kept)
    print("SKIPPED PRICE:", skipped_price)
    print("SKIPPED STOCK:", skipped_stock)

    return variants


# =========================
# XML BUILD
# =========================

def slugify(text):

    if not text:
        return "category"

    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)

    return text.strip("-")


def build_xml(products):

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write("<products>\n")

        for p in products:

            f.write(f'  <product id="{p["id"]}">\n')
            f.write(f'    <title><![CDATA[{p["title"]}]]></title>\n')
            f.write(f'    <description><![CDATA[{p["description"]}]]></description>\n')
            f.write(f'    <price>{p["price"]}</price>\n')
            f.write(f'    <condition>new</condition>\n')
            f.write(f'    <stock>{p["inventory"]}</stock>\n')
            f.write(f'    <ean_code><![CDATA[{p["barcode"]}]]></ean_code>\n')
            f.write(f'    <manufacturer_code><![CDATA[{p["sku"]}]]></manufacturer_code>\n')
            f.write(f'    <manufacturer><![CDATA[{p["vendor"]}]]></manufacturer>\n')
            f.write(f'    <model><![CDATA[{p["sku"]}]]></model>\n')
            f.write(f'    <image_url><![CDATA[{p["image"]}]]></image_url>\n')
            f.write(f'    <product_url><![CDATA[https://glamur.ee/products/{p["handle"]}?variant={p["id"]}]]></product_url>\n')
            f.write(f'    <category_id>0</category_id>\n')
            f.write(f'    <category_name><![CDATA[{p["productType"]}]]></category_name>\n')
            f.write(f'    <category_link><![CDATA[https://glamur.ee/collections/{slugify(p["vendor"])}]]></category_link>\n')
            f.write(f'    <delivery_price>4.49</delivery_price>\n')
            f.write(f'    <delivery_time>10</delivery_time>\n')
            f.write("  </product>\n")

        f.write("</products>\n")

    print("\nXML CREATED:", len(products))


# =========================
# MAIN
# =========================

if __name__ == "__main__":

    print("START FETCHING SHOPIFY DATA\n")

    products = fetch_products()

    print("\nBUILDING XML\n")

    build_xml(products)

    print("\nDONE")
