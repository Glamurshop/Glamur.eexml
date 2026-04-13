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
# DUMMY PRODUCT
# =========================

def get_dummy_product():
    return [{
        "id": "999999999",
        "title": "Feed temporarily disabled",
        "handle": "feed-disabled",
        "vendor": "Glamur",
        "sku": "DISABLED",
        "barcode": "",
        "price": "1000.00",
        "inventory": 1,
        "image": "",
        "description": "Feed is temporarily disabled",
        "productType": "Disabled"
    }]


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
            f.write(f'    <delivery_price>3.49</delivery_price>\n')
            f.write(f'    <delivery_time>4</delivery_time>\n')
            f.write(f'  </product>\n')

        f.write("</products>\n")

    print("\nXML CREATED:", len(products))


# =========================
# MAIN
# =========================

if __name__ == "__main__":

    print("GENERATING DUMMY XML FEED...\n")

    products = get_dummy_product()

    build_xml(products)

    print("\nDONE")
