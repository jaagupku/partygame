# Retailer parser fixtures

Captured from public retailer HTML on 2026-09-19. Fixtures retain relevant product
cards, JSON-LD and price elements; unrelated navigation and scripts are omitted.

- `rimi.html`: variable-weight bananas, regular-price cottage cheese, discounted
  packaged dairy with its explicit regular price.
- `rimi-more.html`: first twelve cards from
  `https://www.rimi.ee/epood/ee/otsing?currentPage=4`, including a fixed-size water
  bottle and packaged cheese, and records the adapter must exclude.
- `klick.html` and `klick-0.html`: `https://www.klick.ee/nutitelefon-xiaomi-redmi-note-15-5g-6-128gb`
- `klick-1.html`: `https://www.klick.ee/sulearvuti-lenovo-v15-g4-ryzen3-16gb-512gb-w11p-must-1`
- `klick-2.html`: `https://www.klick.ee/korvaklapid-jlab-go-pop-anc`
- `klick-3.html`: `https://www.klick.ee/monitor-aoc-c32g42ze-32`

Tests also derive explicit mutations for unavailable/used goods, missing regular
prices, loyalty-only discounts, installment labels, missing images, malformed
JSON-LD and absent breadcrumb categories. These mutations are test cases, not
claims that the captured retailer pages contained those errors.
