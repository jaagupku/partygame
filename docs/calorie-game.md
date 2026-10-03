# Calorie Guessing

Calorie Guessing shows packaged-product photos from Open Food Facts. Players
enter whole kcal or choose the higher-calorie product. Mixed games contain
ceil(n/2) guesses and floor(n/2) comparisons. Food uses kcal per 100 g; drinks use
kcal per 100 ml. Comparisons always use the same basis and distinct rounded
values. Values describe the product as sold, not prepared servings.

Setup supports 5/10/15/20 questions, 15/30/45/60-second answers, 4/6/8/10/15-second
automatic reveals, and automatic or hosted progression. Defaults are mixed,
10 questions, 30-second answers, 4-second reveals, automatic. Ready toggles speed
up automatic reveals by 15% per ready player. Host-paced reveals advance manually.

Scoring is `round_half_up(1000 * max(0, 1 - abs(guess - target) / target))`.
Targets are rounded half-up to whole kcal before selection and evaluation.
Zero targets are excluded. Correct comparisons award 1,000 points, missing
answers award zero, and speed does not affect scores. Guesses must be whole
numbers from zero through 1,000,000.

## Data and operation

Apply the additive migration, then populate the local dataset:

```sh
docker compose exec api poetry run alembic upgrade head
docker compose exec api python -m partygame.service.calories.refresh
```

Compose includes a separate `calorie-scheduler` using the API image and shared
media volume. It refreshes missing data on startup and refreshes weekly on
Monday at 04:00 UTC. Production can run the same image with
`python -m partygame.service.calories.refresh --schedule`, using the same
Postgres, Valkey, and MEDIA_ROOT configuration. Run migrations before the worker.

The default refresh reads up to 400 candidates, half from Estonia-filtered
searches and half internationally. `--max-pages 2`, `4`, or `6` changes the bound
(100 candidates per page). Requests identify Mänguõhtu, search requests are
spaced seven seconds apart, and transient failures use bounded retries/backoff.
Only official HTTPS API/image hosts and redirects are accepted.

Products need a name, barcode, front image, positive as-sold `energy-kcal_100g`,
no reported data-quality errors, and a recognized food/drink category consistent
with explicit package/serving mass or volume units. Ambiguous, prepared-only,
zero-calorie, supplemental, and implausible records are excluded. The `_100g`
field also represents 100 ml for drinks: its suffix alone does not identify units.
Images must pass the existing readability, format, size, and decoding checks.
These checks do not identify every visible calorie label; inspect representative
front photos when changing the adapter or before public launch.

Selection favors Estonian products, adding international records only until the
pool can complete the requested game. Products do not repeat within a session.
The generator spreads selection across recognized categories. A dataset is
published only when it supports 20 questions in every mode. Publication is atomic;
failures preserve the last successful version and remove staged images. Logs
report accepted records, rejected records/images, and the published version.

Prepared sessions freeze products, answers, dataset version, seed, and generator
version. Leases retain images for active lobbies, including continued games.
Superseded unreferenced versions are removed after a two-hour grace period.
Gameplay makes no requests to Open Food Facts.

## Interfaces and attribution

Create/continue requests use `game_type: "calorie_guessing"`, `host_enabled`, and
`calorie_settings: {mode, questions, answer_seconds, reveal_seconds}`.
`GET /api/v1/game-types/calorie_guessing/availability` reports feasible settings
and capture time, never answers. Insufficient content returns HTTP 409 with
`calorie_content_unavailable`. Public runtime calorie fields contain cards and
units; calorie values, source URLs, and player results appear only at reveal.
The existing `price_reveal_ready` event and reveal timer fields are shared by
both product games for compatibility.

Data and photos are attributed to Open Food Facts contributors. Setup links to
`GET /api/v1/game-types/calorie_guessing/dataset`, a downloadable snapshot with
ODbL database, Database Contents License, CC BY-SA image-license links, original
image URLs, and product provenance. This public export intentionally contains
the source nutrition values; gameplay payloads do not expose them early.

## Validation

Run backend tests, frontend checks, and isolated browser scenarios:

```sh
docker compose exec api poetry run pytest
pnpm --dir frontend run check
pnpm --dir frontend run lint
pnpm --dir frontend run test
pnpm --dir frontend run build
./scripts/test-price-browser.sh calorie-game.spec.ts
```

The browser runner uses a dedicated Compose project and guarded synthetic fixture
database; it never seeds the development dataset. Both ingestion schedulers are
disabled there. Screenshots and traces are written under `frontend/test-results`.
Database tests require `POSTGRES_TEST_DATABASE_URL` pointing to a disposable
Postgres database: the fixtures create and drop tables. Live ingestion validation
is separate from fixture-based tests.
