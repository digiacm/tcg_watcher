#!/usr/bin/env python3
"""
TCG Restock/Preorder Watcher (Schweiz)
Prüft konfigurierte Shops auf Pokemon- und Dragon Ball-Produkte
und meldet neue Restocks / Preorders per Discord-Webhook.
"""

import json
import os
import re
import sys
import time
import requests
from bs4 import BeautifulSoup

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
STATE_PATH = os.path.join(os.path.dirname(__file__), "state.json")

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def matches_keywords(text, keyword_groups):
    text_lower = text.lower()
    for _, words in keyword_groups.items():
        for w in words:
            if w.lower() in text_lower:
                return True
    return False


# Merchandise, das faelschlicherweise auf "dragon ball" o.ae. anspringen wuerde,
# obwohl es keine TCG-Karten/Booster/Displays sind (z.B. Actionfiguren).
EXCLUDE_TERMS = [
    "funko", "figur", "figure", "plüsch", "plush", "statue",
    "dxf", "solid edge works", "blood of saiyans", "colosseum",
]


def is_merchandise(text):
    text_lower = text.lower()
    return any(term in text_lower for term in EXCLUDE_TERMS)


def check_woocommerce_shop(shop, keyword_groups):
    found = {}

    for url in shop["urls"]:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"[ERROR] {shop['name']}: Konnte {url} nicht laden ({e})")
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        product_links = soup.find_all("a", href=re.compile(r"/product/[^/]+/?$"))

        for link in product_links:
            href = link.get("href")

            container = link
            for _ in range(4):
                if container.parent:
                    container = container.parent
                if container.name in ("li", "article", "div") and len(container.get_text(strip=True)) > 20:
                    break

            block_text = container.get_text(" ", strip=True)

            title = link.get_text(strip=True)
            if not title:
                img = container.find("img")
                if img and img.get("alt"):
                    title = img["alt"]
            if not title:
                continue

            if not matches_keywords(title, keyword_groups):
                continue
            if is_merchandise(title):
                continue

            block_lower = block_text.lower()
            sold_out = "ausverkauft" in block_lower
            preorder = "vorbestellung" in block_lower

            available = (not sold_out) or preorder

            if href not in found or len(title) > len(found[href]["title"]):
                found[href] = {
                    "id": f"{shop['name']}:{href}",
                    "shop": shop["name"],
                    "title": title,
                    "url": href,
                    "available": available,
                    "preorder": preorder,
                }

    return list(found.values())


def send_discord(title, url, shop, label, color):
    if not DISCORD_WEBHOOK_URL:
        print("[WARN] DISCORD_WEBHOOK_URL fehlt. Nachricht nicht gesendet:")
        print(f"{label} | {shop} | {title} | {url}")
        return
    payload = {
        "embeds": [
            {
                "title": title,
                "url": url,
                "description": f"**{label}** bei **{shop}**",
                "color": color,
            }
        ]
    }
    try:
        r = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=15)
        if r.status_code not in (200, 204):
            print(f"[ERROR] Discord-Versand fehlgeschlagen: {r.status_code} {r.text}")
    except requests.RequestException as e:
        print(f"[ERROR] Discord-Request fehlgeschlagen: {e}")


def check_shopify_shop(shop, keyword_groups):
    found = []
    base = shop["base_url"].rstrip("/")
    page = 1
    while True:
        url = f"{base}/products.json?limit=250&page={page}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[ERROR] {shop['name']}: Konnte {url} nicht laden ({e})")
            break

        products = data.get("products", [])
        if not products:
            break

        for p in products:
            title = p.get("title", "")
            product_type = p.get("product_type", "")
            tags = " ".join(p.get("tags", []))
            searchable = f"{title} {product_type} {tags}"

            if not matches_keywords(searchable, keyword_groups):
                continue
            if is_merchandise(searchable):
                continue

            variants = p.get("variants", [])
            any_available = any(v.get("available") for v in variants)
            handle = p.get("handle", "")
            product_url = f"{base}/products/{handle}"

            found.append({
                "id": f"{shop['name']}:{p.get('id')}",
                "shop": shop["name"],
                "title": title,
                "url": product_url,
                "available": any_available,
            })

        page += 1
        if page > 20:
            break
        time.sleep(0.5)

    return found


def check_custom_shop(shop, keyword_groups):
    found = []
    sel = shop["selectors"]

    for url in shop["urls"]:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"[ERROR] {shop['name']}: Konnte {url} nicht laden ({e})")
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        products = soup.select(sel["product"])

        for prod in products:
            title_el = prod.select_one(sel["title"])
            link_el = prod.select_one(sel["link"])
            avail_el = prod.select_one(sel.get("availability", ""))

            if not title_el:
                continue
            title = title_el.get_text(strip=True)

            if not matches_keywords(title, keyword_groups):
                continue
            if is_merchandise(title):
                continue

            href = link_el.get("href") if link_el else url
            if href and href.startswith("/"):
                from urllib.parse import urljoin
                href = urljoin(url, href)

            avail_text = avail_el.get_text(strip=True).lower() if avail_el else ""
            in_stock = sel.get("in_stock_text", "").lower() in avail_text
            preorder = sel.get("preorder_text", "").lower() in avail_text

            found.append({
                "id": f"{shop['name']}:{title}",
                "shop": shop["name"],
                "title": title,
                "url": href,
                "available": in_stock or preorder,
                "preorder": preorder,
            })

    return found


def main():
    config = load_json(CONFIG_PATH, {})
    state = load_json(STATE_PATH, {})
    keyword_groups = config.get("keywords", {})

    is_first_run = "__meta__" not in state
    if is_first_run:
        print("[INFO] Erster Lauf erkannt: Bestand wird eingelesen, ohne Meldungen zu senden.")
        state["__meta__"] = {"seeded": True}

    new_alerts = []

    for shop in config.get("shops", []):
        if not shop.get("enabled", True):
            continue

        print(f"Prüfe Shop: {shop['name']} ({shop['type']})")

        if shop["type"] == "shopify":
            items = check_shopify_shop(shop, keyword_groups)
        elif shop["type"] == "woocommerce":
            items = check_woocommerce_shop(shop, keyword_groups)
        elif shop["type"] == "custom":
            items = check_custom_shop(shop, keyword_groups)
        else:
            print(f"[WARN] Unbekannter Shop-Typ: {shop['type']}")
            continue

        for item in items:
            item_id = item["id"]
            was_available = state.get(item_id, {}).get("available", False)
            now_available = item.get("available", False)

            if not is_first_run and now_available and not was_available:
                is_preorder = item.get("preorder")
                label = "PREORDER" if is_preorder else "RESTOCK"
                color = 0x5865F2 if is_preorder else 0x57F287
                new_alerts.append({
                    "title": item["title"],
                    "url": item["url"],
                    "shop": item["shop"],
                    "label": label,
                    "color": color,
                })

            state[item_id] = {
                "available": now_available,
                "title": item["title"],
                "shop": item["shop"],
                "url": item["url"],
            }

    if new_alerts:
        print(f"{len(new_alerts)} neue Meldung(en) gefunden.")
        for alert in new_alerts:
            send_discord(
                title=alert["title"],
                url=alert["url"],
                shop=alert["shop"],
                label=alert["label"],
                color=alert["color"],
            )
            time.sleep(1)
    else:
        print("Keine neuen Restocks/Preorders gefunden.")

    save_json(STATE_PATH, state)


if __name__ == "__main__":
    main()
