# Price Guessing

Price Guessing generates frozen sessions from recorded Rimi grocery and Klick
new-electronics prices. The launch screen offers guess, compare, or mixed mode;
groceries, electronics, or both; 5/10/15/20 questions; 15/30/45/60 seconds; and
host-paced or automatic progression. Defaults are mixed/both/10/30/automatic.

Regular prices include VAT and exclude discounts, membership deals, deposits,
delivery and monthly installments. Grocery pack size and electronics model are
shown with clean product images. Capture dates are visible in setup and reveal;
these are recorded prices, not a promise about today's checkout price.

Guess scoring is `round_half_up(1000 * max(0, 1 - abs(guess - price) / price))`.
Each player is scored independently with no speed bonus. Comparisons award
1,000 points for the correct card. Missing answers award zero. Money is stored
as integer cents and guesses are converted with decimal arithmetic.

## Data and deployment

Run the additive migration before serving price-game endpoints:

```sh
docker compose exec api poetry run alembic upgrade head
```

Refresh explicitly with:

```sh
docker compose exec api poetry run python -m partygame.service.prices.refresh
```

`--source rimi` or `--source klick` limits a refresh to one source. `--max-pages`
(default 80, capped at 200) bounds page retrieval; Rimi uses at most 10 listing
pages. Klick interleaves phone, laptop, headphone and monitor category listings,
then supplements them with campaign and sitemap links within the page budget.
Product detail JSON-LD identifies the exact Klick model; its explicit Tavahind
is used for discounted items. Listing-level original-price markup is not trusted.

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
`price_settings: {mode, product_range, questions, answer_seconds}`. It does not
need `definition_id`. Insufficient content returns HTTP 409 with
`price_content_unavailable`. Existing Trivia requests remain compatible.

Before reveal, runtime projections contain only opaque card IDs, product titles,
details and cached image URLs. Prices, source links and player results are added
only during reveal. This also applies to next-question previews, patches and
reconnect snapshots. Generated sessions are not saved as editable quiz packs.

## Tests

Parser fixtures in `api/tests/fixtures/prices` contain excerpts captured from
public retailer pages on 2026-09-19. They exercise actual price and image markup
without network calls. Source parsing, matching, generation, scoring, scheduler
calculation, locking, publication failure and lease cleanup have separate tests.
Set POSTGRES_TEST_DATABASE_URL to a disposable database for the database tests;
those fixtures create and drop tables. Never point it at development or production.

## Selection and publication quality

Generator `price-v2` spreads questions across retailer categories, prefers familiar
Estonian grocery brands and household electronics within those categories, and
avoids consecutive questions from the same category when alternatives remain.
These preferences are editorial rules in `service/prices/selection.py`, not claims
about sales popularity. Seeded ordering still determines ties. Pair selection
preserves maximum-matching capacity and the original price-ratio rules.

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
