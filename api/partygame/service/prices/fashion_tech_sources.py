"""Public product-page adapters for clothing and additional electronics."""

import json
import re
from urllib.parse import urljoin, urlparse

from partygame.schemas.price_game import PriceProduct
from partygame.service.prices.home_sources import meta
from partygame.service.prices.scoring import parse_euros
from partygame.service.prices.sources import Document

LISTINGS = {
    "arvutitark": tuple(
        ("https://arvutitark.ee/" + path, category)
        for path, category in (
            ("arvutikomponendid/protsessorid-cpu", "Protsessorid (CPU)"),
            ("arvutikomponendid/graafikakaardid-vga", "Graafikakaardid"),
            ("arvutikomponendid/malud-ram", "Operatiivmälud"),
            ("arvutikomponendid/andmekandjad/pooljuhtkettad-ssd", "SSD"),
            ("arvutid-ja-lisad/lisaseadmed/hiired", "Hiired"),
            ("arvutid-ja-lisad/lisaseadmed/klaviatuurid", "Klaviatuurid"),
        )
    ),
    "reserved": tuple(
        ("https://www.reserved.com/ee/et/" + path, category)
        for path, category in (
            ("mehed/t-sargid", "T-shirts"),
            ("mehed/puksid", "Trousers"),
            ("mehed/sargid", "Shirts"),
            ("naised/kleidid", "Dresses"),
        )
    ),
}
HOSTS = {"arvutitark": "arvutitark.ee", "reserved": "www.reserved.com"}
IMAGE_HOSTS = {
    "arvutitark": {"media.arvutitark.ee"},
    "reserved": {"static.reserved.com"},
}


def structured(root):
    for node in root.nodes():
        if node.tag == "script" and node.attrs.get("type") == "application/ld+json":
            try:
                data = json.loads(node.text())
                entries = data.get("@graph", [data]) if isinstance(data, dict) else data
                if isinstance(entries, list):
                    yield from (entry for entry in entries if isinstance(entry, dict))
            except ValueError:
                continue


def embedded_object(root, pattern):
    """Decode only JSON data at a known assignment; never execute retailer scripts."""
    for node in root.nodes():
        if node.tag != "script":
            continue
        match = re.search(pattern, node.text())
        if match:
            data, _ = json.JSONDecoder().raw_decode(node.text()[match.end() :].lstrip())
            if isinstance(data, dict):
                return data
    return {}


def safe_url(url, hosts):
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in hosts and parsed.port in (None, 443)


def product_links(html, source):
    root = Document(html).root
    links = []
    for node in root.nodes():
        if node.tag != "a":
            continue
        url = urljoin("https://" + HOSTS[source], node.attrs.get("href", "")).split("?")[0]
        path = urlparse(url).path
        if not safe_url(url, {HOSTS[source]}):
            continue
        if (
            source == "arvutitark"
            and "catalogue-product-link" in node.attrs.get("class", "").split()
        ) or (source == "reserved" and re.fullmatch(r"/ee/et/[^/]+-[a-z0-9]{5}-[a-z0-9]{3}", path)):
            links.append(url)
    return list(dict.fromkeys(links))


def breadcrumb_category(entries):
    for entry in entries:
        if entry.get("@type") == "BreadcrumbList":
            crumbs = entry.get("itemListElement", [])
            if crumbs:
                last = crumbs[-1]
                return last.get("name") or last.get("item", {}).get("name", "")
    return ""


def parse_arvutitark(html, captured_at, category=""):
    root = Document(html).root
    try:
        data = embedded_object(root, r'"currentProduct":')
        entries = list(structured(root))
        product = next(p for p in entries if p.get("@type") == "Product")
        offer = product["offers"]
        url = product["url"]
        current, regular = parse_euros(data.get("price")), parse_euros(data.get("original_price"))
        category = breadcrumb_category(entries)
        if (
            data.get("active") is not True
            or data.get("can_be_sold") is not True
            or data.get("type") != "PRODUCT"
            or data.get("price_region") != "EST"
            or offer.get("priceCurrency") != "EUR"
            or not offer.get("availability", "").endswith("/InStock")
            or not regular
            or not current
            or regular < current
            or parse_euros(offer.get("price")) != current
            or url != urljoin("https://arvutitark.ee", data["path"]["et"])
            or product["sku"] != data["sku"]
            or not category
        ):
            return []
        image = product["image"][0]
        if not safe_url(url, {HOSTS["arvutitark"]}) or not safe_url(
            image, IMAGE_HOSTS["arvutitark"]
        ):
            return []
        return [
            PriceProduct(
                id=str(data["id"]),
                retailer="arvutitark",
                product_range="electronics",
                category=category,
                title=product["name"],
                detail=data["sku"],
                price_minor=regular,
                source_url=url,
                image_url=image,
                captured_at=captured_at,
            )
        ]
    except KeyError, ValueError, TypeError, StopIteration, AttributeError, IndexError:
        return []


def parse_reserved(html, captured_at, category=""):
    root = Document(html).root
    try:
        data = embedded_object(
            root, r"window\['getProductData'\]\s*=\s*function\(\)\s*\{\s*return\s+"
        )
        product = next(p for p in structured(root) if p.get("@type") == "Product")
        offer = product["offers"]
        regular, current = parse_euros(data.get("regularPrice")), parse_euros(
            data.get("finalPrice")
        )
        if (
            not category
            or data.get("isSaleable") is not True
            or data.get("isBlocked")
            or data.get("isBlockedToCart")
            or data.get("isComingSoon")
            or data.get("isGiftCard")
            or not any(s.get("isInStock") is True for s in data["sizes"])
            or data.get("currency") != "EUR"
            or offer.get("priceCurrency") != "EUR"
            or not regular
            or not current
            or regular < current
            or current != parse_euros(offer.get("price"))
            or regular != parse_euros(meta(root, "product:original_price:amount"))
            or product["sku"] != data["sku"]
            or offer["url"] != data["url"]
        ):
            return []
        url, image = data["url"], product["image"]
        if not safe_url(url, {HOSTS["reserved"]}) or not safe_url(image, IMAGE_HOSTS["reserved"]):
            return []
        detail = " · ".join(
            filter(None, [data["color"]["name"], data.get("material"), data["sku"]])
        )
        return [
            PriceProduct(
                id=data["sku"],
                retailer="reserved",
                product_range="clothing",
                category=category,
                title="Reserved " + product["name"],
                detail=detail,
                price_minor=regular,
                source_url=url,
                image_url=image,
                captured_at=captured_at,
            )
        ]
    except KeyError, ValueError, TypeError, StopIteration, AttributeError:
        return []


PARSERS = {"arvutitark": parse_arvutitark, "reserved": parse_reserved}
