# Price Guessing

Price Guessing generates frozen sessions from recorded public shop prices:
Rimi groceries, Klick and Arvutitark electronics, Tootemaailm furniture, E-antiik
antiques and vintage items, and affordable clothing from Reserved. H&M and Gucci
are not imported: their public pages were inaccessible during adapter validation.

Setup offers guess, compare, or mixed mode; any nonempty selection of available categories; 5/10/15/20 questions; 15/30/45/60 seconds; 4/6/8/10/15 seconds to show correct prices in automatic mode; and
host-paced or automatic progression. Defaults are mixed/all available/10/30/4/automatic.
During automatic correct-price reveals, each player can toggle Ready. Every ready
player makes the remaining countdown run 15% faster; toggling off removes that
boost without restoring elapsed time. Host-paced reveals advance manually.
Categories without a published dataset stay visible but disabled. A category may
have several retailers; any published retailer keeps it available, so a missing
new retailer does not disable an existing category. The displayed category capture
date is the oldest included source date; reveals retain each product capture date.

Regular prices include VAT and exclude discounts, membership deals, deposits,
delivery and monthly installments. Antique prices are the shop's recorded asking
prices, not appraisals. Capture dates are visible in setup and reveal; recorded
prices do not promise today's checkout price. Product cards show pack size,
model, or available dimensions/material/year information with cached images.

Guess scoring is `round_half_up(1000 * max(0, 1 - abs(guess - price) / price))`.
Each player is scored independently with no speed bonus. Comparisons award
1,000 points for the correct card. Missing answers award zero. Money is stored
as integer cents and guesses are converted with decimal arithmetic.

Guesses require an explicit Submit price action; unfinished input is not automatically
submitted when time expires or the host reveals answers. Players can submit a revised
price or tap a different comparison card while answering remains open. The latest
submitted answer is scored. Rounds still close when all players answer, time expires,
or the host reveals the answer.

## Data and deployment

Run the additive migration before serving price-game endpoints:

```sh
docker compose exec api poetry run alembic upgrade head
```

Refresh explicitly with:

```sh
docker compose exec api poetry run python -m partygame.service.prices.refresh
```

`--source rimi`, `klick`, `arvutitark`, `tootemaailm`, `eantiik`, or `reserved` limits a refresh to one source. `--max-pages`
(default 80, capped at 200) bounds page retrieval; Rimi uses at most 10 listing
pages. Klick interleaves phone, laptop, headphone and monitor category listings,
then supplements them with campaign and sitemap links within the page budget.
Product detail JSON-LD identifies the exact Klick model; its explicit Tavahind
is used for discounted items. Listing-level original-price markup is not trusted.

The furniture adapter interleaves two listing pages each for coffee tables,
chairs, cabinets, and dining tables. It accepts exact, in-stock simple products;
variable products and ambiguous prices are excluded. E-antiik discovery interleaves
searches for furniture, clocks, ceramics, lighting, art, and decor. The adapter
uses explicit editorial object groups because the site's category field describes
age rather than object type. It accepts items labeled Antiik, or items with a
published year at least 20 years old, and always excludes items labeled Uus.
Unknown object types and sold/unavailable products are excluded. Both adapters
count listing and detail pages against `--max-pages`, use product-detail regular
prices, and restrict page/image requests and redirects to known source hosts.

Arvutitark interleaves CPUs, graphics cards, memory, SSDs, mice and keyboards.
Its product state supplies the explicit VAT-inclusive original price, checked
against the same product's EUR offer and model number. Reserved interleaves
T-shirts, trousers, shirts and dresses; it checks regular prices against the
product metadata and requires an available size. Both adapters count listing and
detail requests against the page budget, validate source/image hosts and retain
the same publication quality gates as other retailers. No synthetic data is
published when a retailer fails.

The Compose `price-scheduler` service uses the API image and shared media volume.
It refreshes missing sources on startup, then refreshes on Mondays at 04:00 UTC.
For production run that image with:

```sh
python -m partygame.service.prices.refresh --schedule
```

Give it the same Postgres, Valkey and MEDIA_ROOT configuration as the API and
access to the same media storage. Alternatively, run the one-shot command from
a deployment scheduler at that time. Do not run refreshes in API startup or
request handlers. The scheduler does not replace the API migration step.

A Postgres advisory lock prevents overlapping refresh workers. Publication is
atomic per source and only occurs after valid product images are cached. Failures
retain the last successful source version and log the error; the one-shot command
returns a nonzero status on failure. Refresh logs include version, accepted products, rejected records and
rejected-image counts. Check capture dates and these logs to detect stale sources.
No fabricated product data is used when a retailer is unavailable.

## Persistence and privacy

`price_datasets` stores immutable normalized product snapshots. New sessions
record exact dataset versions, capture times, generator version and seed, then
use private prepared definitions throughout play. `price_dataset_leases` pins
versions used by sessions. Cleanup retains each source's newest version and any
version with a live Valkey lobby; a two-hour grace period covers session creation
and recent publication. Version-owned images are deleted only with unreferenced
superseded datasets. Finished game statistics retain provenance without pinning
product images forever.

The availability endpoint `/api/v1/game-types/price_guessing/availability` returns
supported settings, capture dates and feasible combinations, never prices. A
creation request uses `game_type: "price_guessing"`, `host_enabled`, and
`price_settings: {mode, product_ranges, questions, answer_seconds, reveal_seconds}`, where
`product_ranges` is a nonempty, unique list drawn from `groceries`, `electronics`,
`furniture`, `antiques`, and `clothing`. Availability combinations use the same list field.
Legacy `product_range` requests remain accepted: `both` means groceries plus
electronics. Supplying both formats is invalid. Omitted API settings retain the
legacy groceries/electronics default; the setup screen explicitly sends its selection. It does not
need `definition_id`. Insufficient content returns HTTP 409 with
`price_content_unavailable`. Existing Trivia requests remain compatible.

Before reveal, runtime projections contain only opaque card IDs, product titles,
details and cached image URLs. Prices, source links and player results are added
only during reveal. This also applies to next-question previews, patches and
reconnect snapshots. Generated sessions are not saved as editable quiz packs.

## Tests

Parser fixtures in `api/tests/fixtures/prices` contain excerpts captured from
public retailer pages; dates and source URLs are recorded in that directory. They exercise actual price and image markup
without network calls. Source parsing, matching, generation, scoring, scheduler
calculation, locking, publication failure and lease cleanup have separate tests.
Set POSTGRES_TEST_DATABASE_URL to a disposable database for the database tests;
those fixtures create and drop tables. Never point it at development or production.

## Selection and publication quality

Generator `price-v3` pairs across all selected categories and retailers. The
higher price must be 1.1–3 times the lower price. Cross-category pairs are
preferred whenever they leave enough matching capacity to complete the game;
same-category comparisons remain valid. Maximum matching prevents greedy pair
selection from incorrectly reporting insufficient content.

Selection spreads appearances across broad categories and object groups, counting
both cards in comparisons, and avoids adjacent category overlap where possible.
Existing familiar-product preferences remain editorial rules, not popularity
claims. Products never repeat within a session; retailer plus product ID is the
identity. Seeded ordering determines ties and card positions. Mixed games retain
ceil(n/2) guesses and floor(n/2) comparisons. Availability computes the same unique
product and maximum-pair capacity conditions as session creation.

Klick categories come from the product's JSON-LD breadcrumb trail. Pages without
an associated category are excluded; product titles are never a category fallback.
Discounts without an explicit regular price and ambiguous price strings are excluded.
The Rimi adapter uses loaded product images rather than blurred lazy-load placeholders.

Every newly published source version must have:

- At least 40 distinct products, with unique IDs, source URLs and descriptions.
- At least three categories containing four or more products each.
- Enough comparable, distinct products to generate 20 questions in each mode.
- Decodable JPEG/PNG/WebP images, at least 256 pixels on each side and at most
  16 million pixels. Truncated, animated and blank images are rejected.
- At least half the product coverage of the previous successful source version.
- No regular-price change over 50% for an existing product without explicit review.

The image checks establish basic readability; they do not automatically establish
that a photograph is the correct product or detect all price overlays. Inspect
browser artifacts and sampled real products when changing adapters.

Failed checks leave the previous version active and remove newly staged images.
After independently verifying a legitimate large price change, an operator may run:

```sh
docker compose exec api poetry run python -m partygame.service.prices.refresh --source klick --accept-price-changes
```

This flag only relaxes the price-change gate. It cannot be combined with
`--schedule`; other quality gates always apply. The explicit override is logged.
Existing frozen sessions keep their original generator provenance and product data.

## Repeatable browser checks

Install the frontend dependencies and Chromium once:

```sh
cd frontend
pnpm install --frozen-lockfile
pnpm exec playwright install chromium
```

From the repository root run:

```sh
./scripts/test-price-browser.sh
```

The runner creates a dedicated `partygame-price-e2e` Compose project on port 18080,
seeds synthetic images/products into the guarded `partygame_price_e2e` database,
and runs Playwright. No retailer requests or development datasets are used.
The scheduler is disabled. The runner removes only its isolated containers and
volumes on exit. Set `PRICE_E2E_PORT` to change the test port.

Coverage includes all modes and progression settings, decimal validation, keyboard
selection, pre-reveal privacy, product order, reconnects, mobile layout, centered
large-screen images, English/Estonian reveals, empty/error states, and automatic
progression through a timeout and finale. Screenshots and failure traces are written
to `frontend/test-results`; screenshot/layout checks are performed during development,
not deferred until after the implementation is declared complete.
