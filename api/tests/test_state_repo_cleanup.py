import pytest

from partygame import schemas
from partygame.state import GameKeyFactory, GameStateRepository


class FakePipeline:
    def __init__(self, redis):
        self.redis = redis
        self.operations: list[tuple[str, tuple]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def expire(self, key: str, ttl_seconds: int):
        self.operations.append(("expire", (key, ttl_seconds)))

    def publish(self, channel: str, payload: str):
        self.operations.append(("publish", (channel, payload)))

    async def execute(self):
        for operation, args in self.operations:
            if operation == "expire":
                await self.redis.expire(*args)
            elif operation == "publish":
                self.redis.published.append(args)
        self.operations.clear()


class FakeRedis:
    def __init__(self):
        self.strings: dict[str, str] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.sorted_sets: dict[str, dict[str, int]] = {}
        self.sets: dict[str, set[str]] = {}
        self.ttls: dict[str, int] = {}
        self.published: list[tuple[str, str]] = []

    async def set(self, key: str, value: str):
        self.strings[key] = value

    async def get(self, key: str):
        return self.strings.get(key)

    async def hset(self, key: str, field=None, value=None, mapping=None):
        self.hashes.setdefault(key, {})
        if mapping is not None:
            self.hashes[key].update({name: str(item) for name, item in mapping.items()})
        elif field is not None:
            self.hashes[key][field] = str(value)

    async def hgetall(self, key: str):
        return dict(self.hashes.get(key, {}))

    async def hget(self, key: str, field: str):
        return self.hashes.get(key, {}).get(field)

    async def hexists(self, key: str, field: str):
        return field in self.hashes.get(key, {})

    async def zadd(self, key: str, mapping: dict[str, int]):
        self.sorted_sets.setdefault(key, {}).update(mapping)

    async def zrange(self, key: str, start: int, end: int, withscores: bool = True):
        items = list(self.sorted_sets.get(key, {}).items())
        if withscores:
            return items
        return [member for member, _score in items]

    async def zscore(self, key: str, member: str):
        return self.sorted_sets.get(key, {}).get(member)

    async def zrem(self, key: str, member: str):
        self.sorted_sets.get(key, {}).pop(member, None)

    async def sadd(self, key: str, *values: str):
        self.sets.setdefault(key, set()).update(values)

    async def smembers(self, key: str):
        return set(self.sets.get(key, set()))

    async def expire(self, key: str, ttl_seconds: int):
        if key in self.strings or key in self.hashes or key in self.sorted_sets or key in self.sets:
            self.ttls[key] = ttl_seconds

    async def delete(self, *keys: str):
        for key in keys:
            self.strings.pop(key, None)
            self.hashes.pop(key, None)
            self.sorted_sets.pop(key, None)
            self.sets.pop(key, None)
            self.ttls.pop(key, None)

    def pipeline(self, transaction: bool = False):
        return FakePipeline(self)


class FakeMediaStorage:
    def __init__(self):
        self.deleted_assets: list[str] = []

    async def delete(self, asset_id: str):
        self.deleted_assets.append(asset_id)


@pytest.mark.asyncio
async def test_game_state_repository_registers_all_game_keys_and_applies_ttl():
    redis = FakeRedis()
    repo = GameStateRepository(redis)
    lobby = schemas.Lobby(id="g1", join_code="ABCDE")
    player = schemas.Player(id="p1", game_id="g1", name="Alice")

    await repo.create_lobby(lobby)
    await repo.create_player(player)
    await repo.set_step_cache("g1", {"step_id": "s1"})
    await repo.set_component_state("g1", "c1", {"active": True})
    await repo.apply_game_ttl("g1", 123)

    assert await repo.get_game_id_from_join_code("ABCDE") == "g1"
    assert await redis.smembers(GameKeyFactory.game_keys("g1")) == {
        GameKeyFactory.join_code("ABCDE"),
        GameKeyFactory.game_meta("g1"),
        GameKeyFactory.game_scores("g1"),
        GameKeyFactory.game_player("g1", "p1"),
        GameKeyFactory.game_steps("g1"),
        GameKeyFactory.game_component("g1", "c1"),
    }
    assert redis.ttls == {
        GameKeyFactory.join_code("ABCDE"): 123,
        GameKeyFactory.game_keys("g1"): 123,
        GameKeyFactory.game_meta("g1"): 123,
        GameKeyFactory.game_scores("g1"): 123,
        GameKeyFactory.game_player("g1", "p1"): 123,
        GameKeyFactory.game_steps("g1"): 123,
        GameKeyFactory.game_component("g1", "c1"): 123,
    }


@pytest.mark.asyncio
async def test_delete_game_removes_join_code_and_registry():
    redis = FakeRedis()
    repo = GameStateRepository(redis)
    lobby = schemas.Lobby(id="g1", join_code="ABCDE")

    await repo.create_lobby(lobby)
    await repo.delete_game("g1")

    assert await repo.get_game_id_from_join_code("ABCDE") is None
    assert await redis.smembers(GameKeyFactory.game_keys("g1")) == set()


@pytest.mark.asyncio
async def test_delete_game_cleans_custom_avatar_assets_only():
    redis = FakeRedis()
    repo = GameStateRepository(redis)
    lobby = schemas.Lobby(id="g1", join_code="ABCDE")
    storage = FakeMediaStorage()

    await repo.create_lobby(lobby)
    await repo.create_player(
        schemas.Player(
            id="p1",
            game_id="g1",
            name="Alice",
            avatar_kind="custom",
            avatar_url="/api/v1/media/custom-1",
            avatar_asset_id="custom-1",
        )
    )
    await repo.create_player(
        schemas.Player(
            id="p2",
            game_id="g1",
            name="Bob",
            avatar_kind="preset",
            avatar_preset_key="fox",
        )
    )

    await repo.delete_game("g1", media_storage=storage)

    assert storage.deleted_assets == ["custom-1"]
