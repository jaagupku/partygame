"""Bounded public-page adapters. Parsers are pure and exercised with captured HTML."""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from partygame.schemas.price_game import PriceProduct
from partygame.service.prices.scoring import parse_euros

log = logging.getLogger(__name__)


@dataclass
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list = field(default_factory=list)

    def nodes(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.nodes()

    def text(self):
        return "".join(
            child.text() if isinstance(child, Node) else child for child in self.children
        )

    def by_class(self, name):
        return next((n for n in self.nodes() if name in n.attrs.get("class", "").split()), None)


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: v or "" for k, v in attrs})
        self.stack[-1].children.append(node)
        if tag not in {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def money(text):
    text = re.sub(r"(?<=\d)[\s\u00a0\u202f]+(?=\d{3}(?:\D|$))", "", text.strip())
    match = re.fullmatch(r"(\d+(?:[.,]\d{2})?)\s*€?(?:\s+per tk)?", text)
    return parse_euros(match[1].replace(",", ".")) if match else None


def parse_rimi(html: str, captured_at: datetime) -> list[PriceProduct]:
    result = []
    candidates = 0
    for node in Document(html).root.nodes():
        if "data-product-code" not in node.attrs:
            continue
        candidates += 1
        try:
            meta = json.loads(node.attrs["data-gtm-eec-product"])
            title = meta["name"]
            # Only packaged groceries with an explicit fixed weight/volume/count.
            if re.search(r"(?:,|\s)kg$", title, re.IGNORECASE) or not re.search(
                r"\d\s*(?:g|kg|ml|l|tk)\b", title, re.IGNORECASE
            ):
                continue
            link = node.by_class("card__url")
            href = link.attrs["href"] if link else ""
            if not any(
                part in href
                for part in [
                    "piimatooted",
                    "liha-",
                    "leivad-",
                    "kuivtooted",
                    "maiustused",
                    "joogid",
                    "sugavkulmutatud",
                    "puuviljad",
                ]
            ):
                continue
            if any(part in href for part in ["alkohol", "olled", "veinid"]):
                continue
            old = node.by_class("card__old-price")
            current = node.by_class("card__price")
            wrapper = node.by_class("card__price-wrapper")
            if (
                old is None
                and wrapper
                and any(
                    marker in wrapper.attrs.get("class", "") for marker in ("discount", "loyalty")
                )
            ):
                continue
            price = old or current
            sr = price.by_class("sr-only") if price else None
            cents = money((sr or price).text().replace("Tavahind:", "")) if price else None
            image = next(
                (n for n in node.nodes() if n.tag == "img" and meta["name"] == n.attrs.get("alt")),
                None,
            )
            available = any(
                n.tag == "button" and "disabled" not in n.attrs and "Lisa ostukorvi" in n.text()
                for n in node.nodes()
            )
            if not cents or not image or not available or meta.get("currency") != "EUR":
                continue
            result.append(
                PriceProduct(
                    id=str(meta["id"]),
                    retailer="rimi",
                    product_range="groceries",
                    category=meta["category"],
                    title=title,
                    detail=re.search(r"\d+[.,]?\d*\s*(?:kg|g|ml|l|tk)\b", title, re.IGNORECASE)[0],
                    price_minor=cents,
                    source_url=urljoin("https://www.rimi.ee", href),
                    image_url=(image.attrs.get("data-src") or image.attrs["src"]).replace(
                        "w_auto", "w_600"
                    ),
                    captured_at=captured_at,
                )
            )
        except KeyError, ValueError, TypeError, AttributeError:
            continue
    log.info("Rimi listing candidates=%d rejected_records=%d", candidates, candidates - len(result))
    return result


def klick_links(html: str):
    return list(
        dict.fromkeys(
            urljoin("https://www.klick.ee", n.attrs["href"])
            for n in Document(html).root.nodes()
            if n.attrs.get("data-testid") == "productLink" and "href" in n.attrs
        )
    )


def parse_klick(html: str, captured_at: datetime) -> list[PriceProduct]:
    root = Document(html).root
    products = []
    breadcrumbs = []
    for node in root.nodes():
        if node.tag != "script" or node.attrs.get("type") != "application/ld+json":
            continue
        try:
            data = json.loads(node.text())
        except ValueError:
            continue
        entries = data.get("@graph", [data]) if isinstance(data, dict) else data
        if isinstance(entries, list):
            breadcrumbs.extend(
                p for p in entries if isinstance(p, dict) and p.get("@type") == "BreadcrumbList"
            )
            products.extend(
                p for p in entries if isinstance(p, dict) and p.get("@type") == "Product"
            )
    result = []
    for product in products:
        title = product.get("name", "")
        source_url = product.get("url", "")
        if not isinstance(title, str) or not title.strip() or not isinstance(source_url, str):
            continue
        category = klick_category(breadcrumbs, source_url)
        if not category:
            continue
        offer = product.get("offers", {})
        if not isinstance(offer, dict) or offer.get("@type") != "Offer":
            continue
        if offer.get("priceCurrency") != "EUR" or not offer.get("availability", "").endswith(
            "/InStock"
        ):
            continue
        if not offer.get("itemCondition", "").endswith("/NewCondition") or re.search(
            r"uue ringi|kasutatud|outlet|alates", title, re.IGNORECASE
        ):
            continue
        old = root.by_class("price-original")
        if old and "Tavahind" in old.text():
            cents = money(old.text().replace("Tavahind", ""))
            current = parse_euros(offer.get("price"))
            if current is None or cents is None or cents < current:
                continue
        else:
            # A discount without an explicit regular price is ambiguous.
            if root.by_class("price-discount"):
                continue
            cents = parse_euros(offer.get("price"))
        images = product.get("image", [])
        image = images[0] if isinstance(images, list) and images else images
        if not cents or not isinstance(image, str) or not image:
            continue
        result.append(
            PriceProduct(
                id=product.get("sku") or product["url"],
                retailer="klick",
                product_range="electronics",
                category=category,
                title=title,
                detail=title,
                price_minor=cents,
                source_url=source_url,
                image_url=image,
                captured_at=captured_at,
            )
        )
    log.info(
        "Klick page candidates=%d rejected_records=%d", len(products), len(products) - len(result)
    )
    return result


def klick_category(breadcrumbs, product_url):
    """Use the deepest retailer category, never infer it from the product name."""
    target = urlparse(product_url)
    if target.scheme != "https" or target.hostname != "www.klick.ee":
        return None
    for breadcrumb in breadcrumbs:
        entries = breadcrumb.get("itemListElement", [])
        if not isinstance(entries, list):
            continue

        def item_url(entry):
            item = entry.get("item", "") if isinstance(entry, dict) else ""
            return item.get("@id", "") if isinstance(item, dict) else item

        # Associate the breadcrumb with this product, avoiding unrelated page trails.
        if not any(item_url(e) == product_url for e in entries):
            continue
        categories = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            url = item_url(entry)
            if (
                not isinstance(url, str)
                or url == product_url
                or not isinstance(entry.get("position"), int)
            ):
                continue
            parsed = urlparse(url)
            if parsed.hostname == "www.klick.ee" and parsed.path.strip("/"):
                categories.append((entry["position"], parsed.path.strip("/")))
        if categories:
            return max(categories)[1]
    return None
