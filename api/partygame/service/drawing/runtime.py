"""Persistent state machine. Mutating callers hold the lobby mutation lock."""

import json
from random import Random
from time import time
from uuid import uuid4

from partygame import schemas
from partygame.core.config import settings
from partygame.schemas.drawing_game import (
    DrawingCommand,
    DrawingGameView,
    MashupArtwork,
    MashupBallot,
    MashupMatchup,
    PreparedDrawingSession,
)
from partygame.service.drawing.rules import allocate_points, assignments
from partygame.service.runtime.end_game import EndGameRuntime
from partygame.service.runtime.evaluation import EvaluationRuntime
from partygame.service.runtime.timing import TimingState
from partygame.state import GameKeyFactory, GameStateRepository

COMPONENT = "drawing_mashup"
DUE_KEY = "drawing_mashup:due"
FINAL_STAGES = ("third_place", "second_place", "first_place", "stats", "scoreboard")


class DrawingError(ValueError):
    pass


class DrawingRuntime:
    def __init__(self, repo: GameStateRepository):
        self.repo = repo

    async def prepared(self, lobby):
        record = await self.repo.get_component_state(lobby.id, "prepared_session")
        return PreparedDrawingSession.model_validate(record["snapshot"])

    async def load(self, lobby):
        record = await self.repo.get_component_state(lobby.id, COMPONENT)
        state = record.get("state")
        if state and state["run_id"] != (lobby.run_id or lobby.id):
            raise DrawingError("stale")
        return state

    async def commit(self, lobby, state, *, publish=True, reschedule=False):
        """State, scores, phase, deadline index and revision commit together."""
        key = GameKeyFactory.game_component(lobby.id, COMPONENT)
        meta = GameKeyFactory.game_meta(lobby.id)
        token = f"{lobby.id}:{state['run_id']}"
        scheduled = await self.repo.redis.zscore(DUE_KEY, token)
        due = time() + 1
        if not reschedule and scheduled is not None:
            due = min(due, scheduled)
        ttl = (
            settings.GAME_FINISHED_TTL_SECONDS
            if state["phase"] == "finished"
            else settings.GAME_IDLE_TTL_SECONDS
        )
        game_state = "paused" if state["paused"] else "running"
        existing_ids = set(await self.repo.get_player_ids(lobby.id, withscores=False))
        scores = {p: score for p, score in state["scores"].items() if p in existing_ids}
        async with self.repo.redis.pipeline(transaction=True) as pipe:
            pipe.hset(key, mapping={"state": json.dumps(state, allow_nan=False)})
            pipe.sadd(GameKeyFactory.game_keys(lobby.id), key)
            pipe.expire(key, ttl)
            pipe.hset(
                meta,
                mapping={
                    "phase": state["phase"],
                    "state": game_state,
                    "starter_id": state["organizer"],
                },
            )
            if scores:
                pipe.zadd(GameKeyFactory.game_scores(lobby.id), scores)
            if publish:
                pipe.hincrby(meta, "state_revision", 1)
            # Keep organizer failover available while the completed lobby is alive.
            pipe.zadd(DUE_KEY, {token: due})
            await pipe.execute()
        lobby.phase = state["phase"]
        lobby.state = schemas.GameState(game_state)
        lobby.starter_id = state["organizer"]
        if publish:
            await self.broadcast(lobby)

    async def start(self, lobby, actor):
        if lobby.state != schemas.GameState.WAITING_FOR_PLAYERS or actor != lobby.starter_id:
            raise DrawingError("stale")
        players = [
            p
            for p in await self.repo.get_players(lobby.id)
            if p.status == schemas.ConnectionStatus.CONNECTED
        ]
        if len(players) < 3:
            raise DrawingError("needs_three_players")
        prepared = await self.prepared(lobby)
        now = time()
        state = {
            "run_id": lobby.run_id or lobby.id,
            "seed": prepared.seed,
            "options": prepared.settings.model_dump(),
            "phase": "writing",
            "phase_id": 1,
            "deadline": now + prepared.settings.writing_seconds,
            "paused": False,
            "remaining": None,
            "roster": {p.id: p.model_dump(mode="json") for p in players},
            "organizer": actor,
            "organizer_offline": None,
            "started_at": now,
            "prompts": {p.id: {"topic": "", "criterion": "", "revision": 0} for p in players},
            "ready": [],
            "matchups": [],
            "artworks": {},
            "matchup_index": 0,
            "ballots": {},
            "scores": {p.id: 0 for p in players},
            "finale_stage": "third_place",
            "metrics": {
                p.id: {"artist_points": 0, "votes": 0, "topic": 0, "criterion": 0} for p in players
            },
        }
        await self.commit(lobby, state)
        await self.repo.apply_game_ttl(lobby.id, settings.GAME_IDLE_TTL_SECONDS)
        return 0

    async def command(self, lobby, actor, command: DrawingCommand):
        if command.run_id != (lobby.run_id or lobby.id):
            raise DrawingError("stale")
        if command.action == "start":
            return await self.start(lobby, actor)
        state = await self.load(lobby)
        if not state or command.phase_id != state["phase_id"] or state["phase"] == "finished":
            raise DrawingError("stale")
        if actor not in state["roster"] or await self.repo.get_player(lobby.id, actor) is None:
            raise DrawingError("forbidden")
        action = command.action
        if action in {"pause", "resume", "advance"}:
            if actor != state["organizer"]:
                raise DrawingError("forbidden")
            if action == "pause" and not state["paused"]:
                state["remaining"] = max(0, state["deadline"] - time())
                state["deadline"] = None
                state["paused"] = True
            elif action == "resume" and state["paused"]:
                state["deadline"] = time() + state["remaining"]
                state["paused"] = False
            elif action == "advance":
                self.advance(state)
            await self.commit(lobby, state)
            return 0
        if state["paused"] or time() >= state["deadline"]:
            raise DrawingError("closed")
        if actor in state["ready"] and action != "ballot":
            if action == "ready":
                return 0
            raise DrawingError("closed")
        revision = 0
        if action == "prompt" and state["phase"] == "writing":
            target = state["prompts"][actor]
            value = {"topic": command.topic.strip(), "criterion": command.criterion.strip()}
            revision = self.update_draft(target, value, command.revision)
        elif action == "draw" and state["phase"] == "drawing":
            target = state["artworks"].get(command.assignment_id)
            if not target or target["owner"] != actor:
                raise DrawingError("forbidden")
            if command.value is not None:
                try:
                    json.dumps(command.value, allow_nan=False)
                    valid = EvaluationRuntime(
                        self.repo, TimingState(), get_step_state=None
                    ).is_valid_drawing_submission(command.value)
                except ValueError, TypeError:
                    valid = False
                if not valid:
                    raise DrawingError("invalid_drawing")
            revision = self.update_draft(target, {"value": command.value}, command.revision)
        elif action == "ballot" and state["phase"] == "voting":
            matchup = state["matchups"][state["matchup_index"]]
            ballot = command.ballot
            if command.matchup_id != matchup["id"] or ballot is None:
                raise DrawingError("stale")
            if actor in self.matchup_artists(state):
                raise DrawingError("invalid_vote")
            if ballot.drawing_id is not None:
                art = state["artworks"].get(ballot.drawing_id)
                if (
                    not art
                    or ballot.drawing_id not in matchup["drawings"]
                    or not art["value"]
                    or art["owner"] == actor
                ):
                    raise DrawingError("invalid_vote")
            if (ballot.topic and matchup["topic_author"] in (None, actor)) or (
                ballot.criterion and matchup["criterion_author"] in (None, actor)
            ):
                raise DrawingError("invalid_vote")
            state["ballots"][actor] = ballot.model_dump()
        elif action == "ready" and state["phase"] in {"writing", "drawing", "voting"}:
            if state["phase"] == "writing" and not all(
                state["prompts"][actor][f] for f in ("topic", "criterion")
            ):
                raise DrawingError("incomplete")
            if state["phase"] == "drawing" and any(
                not a["value"] for a in state["artworks"].values() if a["owner"] == actor
            ):
                raise DrawingError("incomplete")
            state["ready"].append(actor)
            required = set(state["roster"])
            if state["phase"] == "voting":
                required -= self.matchup_artists(state)
            if set(state["ready"]) >= required:
                self.advance(state)
        else:
            raise DrawingError("stale")
        await self.commit(lobby, state, publish=action not in {"prompt", "draw", "ballot"})
        return revision

    @staticmethod
    def update_draft(target, values, expected):
        if target["revision"] != expected:
            if target["revision"] == expected + 1 and all(
                target.get(k) == v for k, v in values.items()
            ):
                return target["revision"]
            raise DrawingError("conflict")
        target.update(values)
        target["revision"] += 1
        return target["revision"]

    def advance(self, state):
        phase = state["phase"]
        state["paused"] = False
        state["remaining"] = None
        state["ready"] = []
        state["phase_id"] += 1
        if phase == "writing":
            self.match(state)
            state["phase"] = "drawing"
            count = 2 if len(state["roster"]) <= 4 else 3
            state["deadline"] = time() + count * state["options"]["drawing_seconds"]
        elif phase == "drawing":
            self.open_vote(state)
        elif phase == "voting":
            self.open_results(state)
        elif phase == "results":
            state["matchup_index"] += 1
            if state["matchup_index"] < len(state["matchups"]):
                self.open_vote(state)
            else:
                state["phase"] = "finished"
                state["finished_at"] = time()
                state["deadline"] = time() + 4.5
        elif phase == "finished":
            i = FINAL_STAGES.index(state["finale_stage"])
            state["finale_stage"] = FINAL_STAGES[min(i + 1, len(FINAL_STAGES) - 1)]
            state["deadline"] = (
                None
                if state["finale_stage"] == "scoreboard"
                else time() + (12 if state["finale_stage"] == "stats" else 4.5)
            )

    def match(self, state):
        ids = list(state["roster"])
        criteria, artists = assignments(len(ids), state["seed"])
        random = Random(state["seed"])
        for topic_index, topic_owner in enumerate(ids):
            criterion_owner = ids[criteria[topic_index]]
            topic = state["prompts"][topic_owner]["topic"]
            criterion = state["prompts"][criterion_owner]["criterion"]
            matchup = {
                "id": uuid4().hex,
                "topic": {"text": topic, "fallback": None if topic else topic_index % 12},
                "criterion": {
                    "text": criterion,
                    "fallback": None if criterion else criteria[topic_index] % 12,
                },
                "topic_author": topic_owner if topic else None,
                "criterion_author": criterion_owner if criterion else None,
                "drawings": [],
                "result": None,
            }
            for player_index in artists[topic_index]:
                aid = uuid4().hex
                state["artworks"][aid] = {
                    "owner": ids[player_index],
                    "topic": matchup["topic"],
                    "criterion": matchup["criterion"],
                    "value": None,
                    "revision": 0,
                }
                matchup["drawings"].append(aid)
            random.shuffle(matchup["drawings"])
            state["matchups"].append(matchup)
        random.shuffle(state["matchups"])

    @staticmethod
    def matchup_artists(state):
        matchup = state["matchups"][state["matchup_index"]]
        return {
            state["artworks"][aid]["owner"]
            for aid in matchup["drawings"]
            if state["artworks"][aid]["value"]
        }

    def open_vote(self, state):
        state["ballots"] = {}
        state["phase"] = "voting"
        state["deadline"] = time() + state["options"]["voting_seconds"]
        matchup = state["matchups"][state["matchup_index"]]
        if not any(state["artworks"][aid]["value"] for aid in matchup["drawings"]):
            self.open_results(state)

    def open_results(self, state):
        self.score(state)
        result = state["matchups"][state["matchup_index"]]["result"]
        duration = 10 + min(8, max(2, len(result["revealed_votes"]) * 0.65))
        result["reveal_duration"] = duration
        state["phase"] = "results"
        state["deadline"] = time() + duration

    def score(self, state):
        matchup = state["matchups"][state["matchup_index"]]
        if matchup["result"] is not None:
            return
        ids = [aid for aid in matchup["drawings"] if state["artworks"][aid]["value"]]
        counts = [sum(b["drawing_id"] == aid for b in state["ballots"].values()) for aid in ids]
        points, allocation = allocate_points(counts)
        result = {
            "allocation": allocation,
            "points": dict(zip(ids, points, strict=True)),
            "votes": dict(zip(ids, counts, strict=True)),
            "topic_points": 0,
            "criterion_points": 0,
            "revealed_votes": [
                {
                    "voter_id": pid,
                    "voter_name": player["name"],
                    "drawing_id": state["ballots"][pid]["drawing_id"],
                }
                for pid, player in state["roster"].items()
                if state["ballots"].get(pid, {}).get("drawing_id") in ids
            ],
        }
        for aid, amount, count in zip(ids, points, counts, strict=True):
            owner = state["artworks"][aid]["owner"]
            state["scores"][owner] += amount
            state["metrics"][owner]["artist_points"] += amount
            state["metrics"][owner]["votes"] += count
        if ids:
            for kind in ("topic", "criterion"):
                owner = matchup[f"{kind}_author"]
                count = sum(b[kind] for b in state["ballots"].values())
                if owner:
                    state["scores"][owner] += 10 * count
                    state["metrics"][owner][kind] += count
                    result[f"{kind}_points"] = 10 * count
        matchup["result"] = result

    def artwork(self, state, aid, *, reveal=False, value=True, viewer=None, result=None):
        art = state["artworks"][aid]
        return MashupArtwork(
            id=aid,
            topic=art["topic"],
            criterion=art["criterion"] if reveal else None,
            value=art["value"] if value else None,
            revision=art["revision"] if viewer == art["owner"] else 0,
            player_id=art["owner"] if reveal else None,
            player_name=state["roster"][art["owner"]]["name"] if reveal else None,
            own=viewer == art["owner"],
            vote_count=(result or {}).get("votes", {}).get(aid, 0),
            points=(result or {}).get("points", {}).get(aid, 0),
        )

    def view(self, state, viewer=None):
        view = DrawingGameView(
            phase=state["phase"],
            phase_id=state["phase_id"],
            deadline=state["deadline"],
            remaining_seconds=state["remaining"],
            server_time=time(),
            paused=state["paused"],
            language=state["options"]["language"],
            participant_ids=list(state["roster"]),
            ready_ids=state["ready"],
            is_participant=viewer in state["roster"],
            matchup_number=min(state["matchup_index"] + 1, len(state["matchups"])),
            matchup_count=len(state["matchups"]),
        )
        if viewer in state["roster"]:
            if state["phase"] == "writing":
                view.prompt = state["prompts"][viewer]
            if state["phase"] == "drawing":
                view.assignments = [
                    self.artwork(state, aid, viewer=viewer)
                    for aid, art in state["artworks"].items()
                    if art["owner"] == viewer
                ]
            if state["phase"] == "voting":
                view.ballot = (
                    MashupBallot.model_validate(state["ballots"][viewer])
                    if viewer in state["ballots"]
                    else None
                )
        if state["phase"] in {"voting", "results"}:
            matchup = state["matchups"][state["matchup_index"]]
            result = matchup["result"] or {}
            reveal = state["phase"] == "results"
            if reveal:
                view.reveal_duration = result.get("reveal_duration")
            view.matchup = MashupMatchup(
                id=matchup["id"],
                topic=matchup["topic"],
                criterion=matchup["criterion"],
                drawings=[
                    self.artwork(state, aid, viewer=viewer, reveal=reveal, result=result)
                    for aid in matchup["drawings"]
                    if state["artworks"][aid]["value"]
                ],
                can_commend_topic=viewer in state["roster"]
                and matchup["topic_author"] not in (None, viewer),
                can_commend_criterion=viewer in state["roster"]
                and matchup["criterion_author"] not in (None, viewer),
                topic_author=(
                    state["roster"][matchup["topic_author"]]["name"]
                    if reveal and matchup["topic_author"]
                    else None
                ),
                criterion_author=(
                    state["roster"][matchup["criterion_author"]]["name"]
                    if reveal and matchup["criterion_author"]
                    else None
                ),
                topic_points=result.get("topic_points", 0),
                criterion_points=result.get("criterion_points", 0),
                allocation=result.get("allocation"),
                revealed_votes=result.get("revealed_votes", []) if reveal else [],
            )
        if state["phase"] == "finished":
            view.gallery = [
                self.artwork(state, aid, reveal=True, value=False, result=m["result"])
                for m in state["matchups"]
                for aid in m["drawings"]
                if state["artworks"][aid]["value"]
            ]
        return view

    async def snapshot(self, lobby, revision=None) -> schemas.RuntimeSnapshotEvent:
        state = await self.load(lobby)
        players = await self.repo.get_players(lobby.id)
        end_game = None
        if state and state["phase"] == "finished":
            finalists = [
                schemas.Player.model_validate(p | {"score": state["scores"][pid]})
                for pid, p in state["roster"].items()
            ]
            standings = EndGameRuntime(self.repo, TimingState())._build_final_standings(
                finalists, None
            )
            cards = []
            for kind in ("votes", "topic", "criterion"):
                best = max((m[kind] for m in state["metrics"].values()), default=0)
                if best:
                    cards.append(
                        schemas.EndGameStatCard(
                            id=f"drawing_{kind}",
                            label=f"drawing_{kind}",
                            value=best,
                            winner_player_ids=[
                                p for p, m in state["metrics"].items() if m[kind] == best
                            ],
                        )
                    )
            end_game = schemas.EndGameState(
                revealed=True,
                sequence_stage=state["finale_stage"],
                autoplay_enabled=True,
                final_standings=standings,
                podium=[s for s in standings if s.place <= 3],
                stats_cards=cards,
                highlight_card_ids=[c.id for c in cards],
            )
        return schemas.RuntimeSnapshotEvent(
            revision=(
                revision if revision is not None else await self.repo.get_state_revision(lobby.id)
            ),
            lobby=schemas.RuntimeLobbyState.model_validate(lobby.model_dump()),
            players=players,
            display_phase=state["phase"] if state else "waiting",
            end_game=end_game,
            drawing_game=self.view(state) if state else DrawingGameView(),
            drawing_private={p: self.view(state, p) for p in state["roster"]} if state else {},
        )

    async def broadcast(self, lobby):
        from partygame.service.player import public_runtime_snapshot

        snapshot = await self.snapshot(lobby)
        payloads = [
            (
                GameKeyFactory.display_channel(lobby.id),
                public_runtime_snapshot(snapshot).model_dump_json(),
            )
        ]
        for p in await self.repo.get_players(lobby.id):
            payloads.append(
                (
                    GameKeyFactory.player_channel(lobby.id, p.id),
                    public_runtime_snapshot(snapshot, viewer_player_id=p.id).model_dump_json(),
                )
            )
        await self.repo.publish_many(payloads)

    async def schedule(self, lobby):
        await self.repo.redis.zadd(DUE_KEY, {f"{lobby.id}:{lobby.run_id or lobby.id}": time() + 1})

    async def tick_waiting(self, lobby, now):
        players = await self.repo.get_players(lobby.id)
        connected = [p.id for p in players if p.status == schemas.ConnectionStatus.CONNECTED]
        record = await self.repo.get_component_state(lobby.id, COMPONENT)
        grace = record.get("waiting_grace", {})
        if lobby.starter_id in connected:
            if grace:
                await self.repo.set_component_state(lobby.id, COMPONENT, {"waiting_grace": {}})
        elif lobby.starter_id:
            if grace.get("organizer") != lobby.starter_id:
                grace = {"organizer": lobby.starter_id, "since": now}
                await self.repo.set_component_state(lobby.id, COMPONENT, {"waiting_grace": grace})
            elif now - grace["since"] >= 15 and connected:
                lobby.starter_id = connected[0]
                await self.repo.set_lobby_fields(lobby.id, starter_id=lobby.starter_id)
                await self.repo.redis.hincrby(
                    GameKeyFactory.game_meta(lobby.id), "state_revision", 1
                )
                await self.broadcast(lobby)
        if not record and grace:
            await self.repo.redis.expire(
                GameKeyFactory.game_component(lobby.id, COMPONENT), settings.GAME_IDLE_TTL_SECONDS
            )
        await self.schedule(lobby)

    async def tick(self, lobby, now=None):
        now = now if now is not None else time()
        state = await self.load(lobby)
        if not state:
            if lobby.state == schemas.GameState.WAITING_FOR_PLAYERS:
                await self.tick_waiting(lobby, now)
            return
        changed = False
        connected = {
            p.id
            for p in await self.repo.get_players(lobby.id)
            if p.status == schemas.ConnectionStatus.CONNECTED
        }
        if state["organizer"] in connected:
            if state["organizer_offline"] is not None:
                state["organizer_offline"] = None
                changed = True
        elif state["organizer_offline"] is None:
            state["organizer_offline"] = now
            changed = True
        elif now - state["organizer_offline"] >= 15:
            replacement = next((p for p in state["roster"] if p in connected), None)
            if replacement:
                state["organizer"] = replacement
                state["organizer_offline"] = None
                changed = True
        if not state["paused"] and state["deadline"] is not None and now >= state["deadline"]:
            self.advance(state)
            changed = True
        if state["phase"] == "finished" and not state.get("archived"):
            from partygame.service.stats import GameStatsArchiver

            # Commit the finished state first; archive is retryable and idempotent by run ID.
            await self.commit(lobby, state)
            await self.repo.apply_game_ttl(lobby.id, settings.GAME_FINISHED_TTL_SECONDS)
            await GameStatsArchiver(self.repo).archive_finished_game(lobby, strict=True)
            state["archived"] = True
            changed = True
        if changed:
            await self.commit(lobby, state, reschedule=True)
        else:
            await self.repo.redis.zadd(DUE_KEY, {f"{lobby.id}:{state['run_id']}": time() + 1})
