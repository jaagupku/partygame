# Adding games

Game types are launch choices, while game definitions are editable content packs.
The catalog (`GET /api/v1/game-types`) lists stable IDs, localization keys,
availability, and supported host modes. Trivia and Price Guessing are available; Price Guessing requires a usable
product dataset. New frontend copy belongs in both languages in `i18n.ts`.

## Preparation and play

Lobby creation validates the type and source permissions, then calls a session
builder. Trivia uses the existing definition provider and the internal round
composer. A prepared session contains a versioned definition snapshot and round
origins. It is stored privately as the `prepared_session` Valkey component,
registered for the lobby's normal TTL and deletion. `session_version` on lobby
metadata distinguishes new sessions from older lobbies that still load live
source definitions. A missing or unsupported new snapshot is an error, never a
reason to silently load different content.

Runtime questions, theme, and statistics resolve the prepared definition. Source
edits or deletion do not change it. Media references are retained, not copied;
external media can still change or disappear. Public lobby responses do not
contain the private record. Existing viewer-specific websocket redaction applies
to its runtime projections, including answer hiding before reveal.

The composer accepts ordered round bundles, copies them, namespaces round and
step IDs by their position, and retains original IDs and provenance separately.
The first bundle supplies the theme. Native scoring is preserved: rounds share
one cumulative score and the existing single finale. There is no normalization,
public composition endpoint, or mixed-session editor yet.

## Generated rounds

A `RoundGenerator[Settings]` accepts typed, validated settings, a seed, and a
`DatasetSnapshot`. It returns round bundles with provenance: source/dataset ID,
dataset version, capture time, generator version, and seed. The deterministic
fixture in `test_game_sessions.py` demonstrates this contract without shipping a
production generator.

The future data pipeline is:

1. A separate ingestion task retrieves and validates an approved external source.
2. It stores a versioned dataset with a capture timestamp.
3. Session preparation selects that version and runs a local generator once.
4. The resulting rounds and provenance are frozen in the private session record.
5. Gameplay and reconnects use that record without external data requests.

To add a playable game, implement its settings and session builder, register it
in the catalog and builder dispatch, and add its localized setup UI and tests.
Keep source credentials and correct answers out of public catalog/setup payloads.
See [Price Guessing](price-game.md) for its implemented data adapters, weekly
refresh, settings, scoring and deployment.

This foundation covers games representable as rounds and steps. A game with a
fundamentally different interaction loop needs explicit runtime and controller
capabilities; it should not be forced into a generated quiz definition.

## Compatibility

Existing definition editing, import/export, and Postgres records are unchanged.
Legacy create requests default to Trivia. New catalog/metadata fields are
additive; deploy backend support before the frontend. Existing lobbies without a
snapshot retain legacy behavior until they expire. The session foundation itself needs no database migration. Price Guessing adds
dataset/lease tables and a separate weekly ingestion worker.

## Continuing a lobby

After the finale, only the player who can start the game (the assigned host or
automatic-mode starter) can prepare another game from their controller. The main
display never shows rematch controls and its management cookie does not grant
access to rematch setup. Setup is local to that browser until
confirmed; other players keep seeing the completed game. Confirmation returns
all connected clients to the waiting lobby, with the same join code and player
credentials, and resets scores. The normal Start Game action starts the new run.

- `GET /api/v1/lobby/{game_id}/setup` returns the current run ID and saved creation
  settings to an authorized manager. Older procedural lobbies report incomplete
  settings so the manager can review defaults explicitly.
- `POST /api/v1/lobby/{game_id}/continue` accepts `expected_run_id` and `settings`
  (the same options as lobby creation). It requires a finished, matching run.
  Preparation or history failures leave the completed run intact.
- `run_id` identifies one game within the stable lobby; `session_version` still
  identifies the prepared snapshot format. Snapshots expose `run_id`, and
  controller/display commands include it to reject actions from an earlier run.
  Commands without it are accepted only for the original run for compatibility.
- Generated games get fresh content with the chosen settings. Replaying the same
  Trivia pack uses its frozen content. Switching packs applies normal access
  checks. Individual generated questions may repeat across games.
- History records use the run ID as `game_id`, and retain the lobby ID in summary
  metadata. No database migration is needed for existing history.

Run `PRICE_E2E_URL=http://localhost pnpm --dir frontend exec playwright test
lobby-continuation.spec.ts` against an existing local stack with Price Guessing
content, or pass `lobby-continuation.spec.ts` to `scripts/test-price-browser.sh`
for the isolated fixture stack.
