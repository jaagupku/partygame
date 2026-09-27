"""Furniture and antiques adapters for public product pages."""

import json
import re
from datetime import datetime
from html import unescape
from urllib.parse import urljoin, urlparse

from partygame.schemas.price_game import PriceProduct
from partygame.service.prices.scoring import parse_euros
from partygame.service.prices.sources import Document, money

FURNITURE_LISTINGS = (
    "https://tootemaailm.ee/diivanilauad/",
    "https://tootemaailm.ee/toolid/",
    "https://tootemaailm.ee/kapid-kummutid/",
    "https://tootemaailm.ee/soogilauad/",
)
# E-antiik's category attribute describes age, not object type. These are explicit
# editorial object groups; unknown titles are excluded rather than guessed.
ANTIQUE_GROUPS = {
    "furniture": r"\b(?:.*laud|.*tool|.*kapp|kummut|riiul|voodi|diivan)(?:id)?\b",
    "clocks": r"\b(?:seina|laua|põranda)?kell\b",
    "ceramics": r"\b(?:vaas|vaasid|kann|taldrik|serviis|kohviserviis|teekann|tass)\b",
    "lighting": r"\b(?:laua|põranda|seina)?lamp|\blühter|\bküünlajalg",
    "art": r"\b(?:.*maal|skulptuur|kuju|.*gravüür)\b",
    "decor": r"\b(?:.*peegel|.*vaip|riidenagi|vihmavarjuhoidja)\b",
}
ANTIQUE_LISTINGS = tuple(
    f"https://www.e-antiik.ee/shop?search={term}"
    for term in ("laud", "kell", "vaas", "lamp", "maal", "peegel")
)


def normalized_text(node):
    return " ".join(node.text().split()) if node else ""


def meta(root, name):
    return next(
        (
            n.attrs.get("content", "")
            for n in root.nodes()
            if n.tag == "meta" and n.attrs.get("property") == name
        ),
        "",
    )


def item(root, prop):
    return next((n for n in root.nodes() if n.attrs.get("itemprop") == prop), None)


def product_links(html, source):
    root = Document(html).root
    if source == "eantiik":
        containers = [
            n for n in root.nodes() if "oe_product_cart" in n.attrs.get("class", "").split()
        ]
        base = "https://www.e-antiik.ee"
        links = [
            n.attrs["href"]
            for card in containers
            for n in card.nodes()
            if n.tag == "a" and n.attrs.get("href", "").startswith("/shop/product/")
        ]
    else:
        base = "https://tootemaailm.ee"
        links = [
            n.attrs["href"]
            for n in root.nodes()
            if n.tag == "a"
            and "woocommerce-LoopProduct-link" in n.attrs.get("class", "").split()
            and "href" in n.attrs
        ]
    return list(dict.fromkeys(urljoin(base, link.split("?")[0]) for link in links))


def parse_tootemaailm(html: str, captured_at: datetime) -> list[PriceProduct]:
    root = Document(html).root
    # Resolve price markup inside the main product, never related products.
    main = next(
        (
            n
            for n in root.nodes()
            if n.attrs.get("id", "").startswith("product-")
            and "product-type-simple" in n.attrs.get("class", "").split()
        ),
        None,
    )
    if main is None or "outofstock" in main.attrs.get("class", "").split():
        return []
    summary = main.by_class("summary")
    if summary is None:
        return []
    price = summary.by_class("price")
    if price is None:
        return []
    old = next((n for n in price.nodes() if n.tag == "del"), None)
    if old is None and (main.by_class("onsale") or any(n.tag == "ins" for n in price.nodes())):
        return []
    amount = (old or price).by_class("woocommerce-Price-amount")
    cents = money(normalized_text(amount))
    if not cents:
        return []
    result = []
    for node in root.nodes():
        if node.tag != "script" or node.attrs.get("type") != "application/ld+json":
            continue
        try:
            data = json.loads(node.text())
            entries = data.get("@graph", [data]) if isinstance(data, dict) else data
            if not isinstance(entries, list):
                continue
            for product in entries:
                if not isinstance(product, dict) or product.get("@type") != "Product":
                    continue
                offer = product.get("offers")
                if not isinstance(offer, dict) or offer.get("@type") != "Offer":
                    continue
                current = parse_euros(offer.get("price"))
                if (
                    offer.get("priceCurrency") != "EUR"
                    or not current
                    or cents < current
                    or (not old and cents != current)
                    or not offer.get("availability", "").endswith("/InStock")
                    or not offer.get("itemCondition", "").endswith("NewCondition")
                ):
                    continue
                url = offer.get("url", "")
                if urlparse(url).hostname != "tootemaailm.ee" or url != meta(root, "og:url"):
                    continue
                category = unescape(product.get("category", ""))
                if not isinstance(category, str) or not category.startswith("Mööbel >"):
                    continue
                images = product.get("image", [])
                image = images[0] if isinstance(images, list) and images else images
                if isinstance(image, dict):
                    image = image.get("url")
                title = product.get("name")
                sku = product.get("sku")
                if not image or not title or not sku:
                    continue
                # Do not show marketing paragraphs (which can contain price hints).
                details = []
                attributes = main.by_class("woocommerce-product-attributes")
                if attributes:
                    for row in attributes.nodes():
                        if row.tag == "tr" and re.search(
                            r"mõõ|materjal|laius|kõrgus|pikkus", row.text(), re.IGNORECASE
                        ):
                            details.append(normalized_text(row))
                result.append(
                    PriceProduct(
                        id=str(sku),
                        retailer="tootemaailm",
                        product_range="furniture",
                        category=category.split(" > ")[-1],
                        title=title,
                        detail=" · ".join(details)[:300] or title,
                        price_minor=cents,
                        source_url=url,
                        image_url=image,
                        captured_at=captured_at,
                    )
                )
        except ValueError, TypeError, KeyError, AttributeError:
            continue
    return result


def parse_eantiik(html: str, captured_at: datetime) -> list[PriceProduct]:
    root = Document(html).root
    main = next((n for n in root.nodes() if n.attrs.get("id") == "product_details"), None)
    if main is None:
        return []
    cart = next((n for n in main.nodes() if n.attrs.get("id") == "add_to_cart"), None)
    if (
        cart is None
        or "disabled" in cart.attrs
        or cart.attrs.get("aria-disabled") == "true"
        or "disabled" in cart.attrs.get("class", "").split()
        or re.search(r"müüdud|välja müüdud|out of stock", normalized_text(main), re.IGNORECASE)
    ):
        return []
    attributes = {}
    for node in root.nodes():
        if node.tag != "tr":
            continue
        cells = [n for n in node.children if getattr(n, "tag", None) == "td"]
        if len(cells) == 2:
            attributes[normalized_text(cells[0])] = normalized_text(cells[1])
    classification = attributes.get("Kategooria", "").casefold()
    year = attributes.get("Aasta", "")
    vintage = year.isdigit() and 0 < int(year) <= captured_at.year - 20
    if classification == "uus" or not (classification == "antiik" or vintage):
        return []
    title = normalized_text(item(main, "name"))
    category = next(
        (
            name
            for name, pattern in ANTIQUE_GROUPS.items()
            if re.search(pattern, title, re.IGNORECASE)
        ),
        None,
    )
    sku = normalized_text(item(main, "sku"))
    current = parse_euros(normalized_text(item(main, "price")))
    regular = next(
        (
            n
            for n in main.nodes()
            if n.attrs.get("data-oe-expression") == "combination_info['list_price']"
        ),
        None,
    )
    cents = money(normalized_text(regular)) if regular else None
    url, image = meta(root, "og:url"), meta(root, "og:image")
    if (
        not category
        or not sku
        or not cents
        or not current
        or cents < current
        or normalized_text(item(main, "priceCurrency")) != "EUR"
        or urlparse(url).hostname != "www.e-antiik.ee"
        or not image
    ):
        return []
    details = [
        f"{key}: {attributes[key]}"
        for key in ("Aasta", "Päritolu", "Materjal", "Seisukord", "Sügavus", "Kõrgus", "Laius")
        if attributes.get(key)
    ]
    return [
        PriceProduct(
            id=sku,
            retailer="eantiik",
            product_range="antiques",
            category=category,
            title=title,
            detail=" · ".join(details)[:400],
            price_minor=cents,
            source_url=url,
            image_url=image,
            captured_at=captured_at,
        )
    ]
