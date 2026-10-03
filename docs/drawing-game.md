# Drawing Mashup / Joonistussegadus

An automatic game for at least three connected players. Create it from the home
catalog or select it when continuing a completed lobby. One run contains writing,
a private drawing queue, then one vote and result reveal per topic.

Each player supplies one broad topic and one voting criterion. Criteria are
secret until voting. Every topic and criterion is used once, with different
authors. Players draw twice with 3–4 participants and three times with 5+.
Assignments never include the artist's own topic. With 4+ participants they also
exclude their own criterion. Three players require a criterion exception.

Every topic with artwork distributes exactly 1,000 artist points according to
valid votes. Integer remainders follow the persisted random artwork order. A sole
artist receives 1,000 automatically; a topic with multiple drawings but no votes
splits the pool equally. No artwork means no artist points. Players whose drawing
is shown cannot vote or commend writing in that matchup; voting can finish once
all eligible voters are done. Each eligible voter may also
commend the topic and criterion for 10 additional points each, excluding their
own writing or built-in fallback text. Commendations remain available when only
one drawing was submitted. Drawing votes stay private until results, when each
voter’s name is shown beside their chosen drawing. Abstentions are not listed; individual writing
commendations remain private.

Defaults: 90 seconds writing, 90 seconds per assigned drawing in a shared queue,
30 seconds per voting matchup, 12–18 seconds for results. Results reveal artists
(1.5 seconds), named votes (2–8 seconds, batched for larger groups), the exact
1,000-point split (2 seconds), writing bonuses (1.5 seconds), and a final summary
(5 seconds). Shared screens and phones follow the server deadline; refresh and
reconnect resume the reveal in progress. Reduced motion uses discrete reveals.
Legacy active results without reveal metadata display a static summary. The
organizer can pause/resume or close a phase early. The next connected participant takes over
after a 15-second organizer disconnection grace period. Deadlines continue
independently of player connections.

## Persistence and protocol

Creation accepts `game_type: drawing_mashup`, `host_enabled: false`, and
`drawing_settings` (`writing_seconds`, `drawing_seconds`, `voting_seconds`,
`language`). Writing/drawing settings accept 30–300 seconds; voting accepts
10–120; language is `en` or `et`. Prepared sessions use version 2 with metadata,
settings, seed, and fallback version, without quiz rounds. Existing games retain
version-1 sessions.

Private runtime state uses the registered `drawing_mashup` Valkey component.
The `drawing_mashup:due` sorted set drives an API-lifespan background worker.
Workers use the lobby mutation lock and recheck deadlines/run IDs. State, scores,
lobby phase, and scheduling commit atomically. Expired/deleted/continued runs are
removed from the due index when encountered. No database migration is needed.

`drawing_command` websocket messages identify their action, run, phase and
request. Drafts use optimistic revisions. The authenticated connection supplies
the actor. Draft acknowledgements are private; progress and transitions publish
viewer-specific snapshots. Controllers receive only their own assignments and
drafts. The shared screen receives no private writing or drawing data before
voting. Duplicate draft retries are safe, and old run/phase commands are rejected.
Results persist a frozen list of final drawing votes and a reveal duration when
scoring occurs. Drawing views include server time for client clock alignment;
only results views include the named votes and reveal duration. Pausing freezes
the countdown and animations; advancing ends the reveal. Scoring still commits
once on the server, independently of animation progress.

The canvas saves locally and to the server. Refresh restores saved work;
reconnection retries pending changes while the phase is still open. At timeout,
missing writing gets localized fallback references and valid nonempty artwork is
finalized. Empty drawings are omitted. Fallback text resolves from `i18n.ts` in
the fixed game language, so different controller UI languages agree on content.

The finale includes drawing-specific highlights and a seven-second looping
gallery alongside standings. Artwork is loaded individually from authenticated
`GET /api/v1/lobby/{game_id}/drawing/{run_id}/{drawing_id}` requests after the run
finishes. Player-cookie requests also identify `player_id`; display-cookie
requests need no player ID. Only metadata appears in finale snapshots. Artwork
expires with the lobby and is removed on continuation. History retains scores
and vote/commendation totals, not a permanent artwork gallery.

## Validation

- `cd api && poetry run pytest tests/test_drawing_game.py`
- `PRICE_E2E_URL=http://localhost pnpm --dir frontend exec playwright test drawing-game.spec.ts`

Browser tests use separate phone contexts and new test lobbies on an existing
stack, with real canvas input, refresh recovery, voting, gallery and rematch.
Deploy the backend before the frontend so new clients have the runtime available.
