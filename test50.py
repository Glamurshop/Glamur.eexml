import requests
import re
from time import sleep

# === 🔹 Shopify API nustatymai ===
SHOPIFY_DOMAIN = "xxcw0w-1f.myshopify.com"
ACCESS_TOKEN = "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"
GRAPHQL_URL = f"https://{SHOPIFY_DOMAIN}/admin/api/2023-10/graphql.json"

HEADERS = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": ACCESS_TOKEN
}

OUTPUT_FILE = "glamur_ee_xml_finalvertimai.xml"
LIMIT = 50000


def fetch_product_variant_prices_with_titles(country_code="EE", locale="et"):
    all_variants = []
    cursor = None
    total_processed = 0

    while True:
        query = f"""
        {{
          productVariants(first: 50{', after: "' + cursor + '"' if cursor else ''}) {{
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

        print("🔵 Užklausa Shopify API...")
        response = requests.post(GRAPHQL_URL, headers=HEADERS, json={"query": query})

        if response.status_code != 200:
            print(f"❌ HTTP klaida: {response.status_code}")
            print(response.text)
            break

        data = response.json()
        if "data" not in data or not data["data"].get("productVariants"):
            print("❌ Tuščias Shopify atsakymas:")
            print(response.text[:500])
            break

        productVariants = data["data"]["productVariants"]

        for edge in productVariants["edges"]:
            node = edge.get("node")
            if not node:
                continue

            product = node.get("product")
            if not product or product.get("status") != "ACTIVE":
                continue

            # 🧠 Ištraukiame vertimus (estoniškus)
            translations = product.get("translations", [])
            title_et = next((t["value"] for t in translations if t["key"] == "title"), None)
            body_et = next((t["value"] for t in translations if t["key"] == "body_html"), None)

            # Jei nėra vertimo – naudok lietuvišką
            title = title_et or product.get("title", "Be pavadinimo")
            description = re.sub(r"<.*?>", "", body_et or product.get("bodyHtml") or "").strip()

            # Toliau kaip įprasta
            contextual = node.get("contextualPricing") or {}
            price_data = contextual.get("price") or {}
            price = float(price_data.get("amount") or 0)
            inventory = node.get("inventoryQuantity", 0)
            if price <= 0 or inventory <= 0:
                continue

            variant_name = " ".join([opt.get("value", "") for opt in node.get("selectedOptions", [])])
            full_title = f"{title} {variant_name}".strip()

            image = (node.get("image") or {}).get("src") or (product.get("featuredImage") or {}).get("src") or ""

            all_variants.append({
                "id": (node.get("id") or "").split("/")[-1],
                "title": full_title,
                "handle": product.get("handle", ""),
                "vendor": product.get("vendor", "Tundmatu"),
                "sku": node.get("sku", ""),
                "barcode": node.get("barcode", ""),
                "price": f"{price:.2f}",
                "inventory": inventory,
                "image": image,
                "description": description,
                "productType": product.get("productType") or product.get("vendor", "Parfüümid")
            })

            total_processed += 1
            if total_processed >= LIMIT:
                print(f"⏹️ Pasiektas limitas ({LIMIT}).")
                return all_variants

        print(f"🔹 Surinkta variantų: {len(all_variants)}")

        if not productVariants["pageInfo"]["hasNextPage"]:
            break

        cursor = productVariants["edges"][-1]["cursor"]
        sleep(0.5)

    return all_variants


def slugify(text):
    if not text:
        return "kategooria"
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def build_xml(variants):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write("<products>\n")

        for v in variants:
            f.write(f'  <product id="{v["id"]}">\n')
            f.write(f'    <title><![CDATA[{v["title"]}]]></title>\n')
            f.write(f'    <description><![CDATA[{v["description"]}]]></description>\n')
            f.write(f'    <price>{v["price"]}</price>\n')
            f.write(f'    <condition>new</condition>\n')
            f.write(f'    <stock>{v["inventory"]}</stock>\n')
            f.write(f'    <ean_code><![CDATA[{v["barcode"]}]]></ean_code>\n')
            f.write(f'    <manufacturer_code><![CDATA[{v["sku"]}]]></manufacturer_code>\n')
            f.write(f'    <manufacturer><![CDATA[{v["vendor"]}]]></manufacturer>\n')
            f.write(f'    <model><![CDATA[{v["sku"]}]]></model>\n')
            f.write(f'    <image_url><![CDATA[{v["image"]}]]></image_url>\n')
            f.write(f'    <product_url><![CDATA[https://glamur.ee/products/{v["handle"]}?variant={v["id"]}]]></product_url>\n')
            f.write(f'    <category_id>0</category_id>\n')
            f.write(f'    <category_name><![CDATA[{v["productType"] or v["vendor"]}]]></category_name>\n')
            f.write(f'    <category_link><![CDATA[https://glamur.ee/collections/{slugify(v["vendor"])}]]></category_link>\n')
            f.write(f'    <delivery_price>4.49</delivery_price>\n')
            f.write(f'    <delivery_time>10</delivery_time>\n')
            f.write("  </product>\n")

        f.write("</products>\n")

    print(f"🎉 Sugeneruotas pilnas XML feedas su {len(variants)} produktais.")


if __name__ == "__main__":
    print("🔄 Pradedamas duomenų surinkimas iš Shopify (su estoniškais vertimais)...")
    try:
        variants = fetch_product_variant_prices_with_titles()
        for v in variants[:5]:
            print(f"🧴 {v['title']} — €{v['price']} — {v['inventory']} tk")
        if variants:
            build_xml(variants)
    except Exception as e:
        print(f"❌ Įvyko klaida: {e}")
