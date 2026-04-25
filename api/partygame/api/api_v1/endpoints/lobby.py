from redis.asyncio import Redis
from fastapi import APIRouter, Depends, HTTPException

from partygame import schemas, service
from partygame.api import deps

router = APIRouter()


@router.get("/join-code/{join_code}", response_model=schemas.Lobby)
async def get_lobby_by_join_code(join_code: str, *, redis: Redis = Depends(deps.get_redis)):
    game_id = await service.lobby.get_id_from_join_code(redis, join_code.upper())
    if game_id is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return await service.lobby.get(redis, game_id)


@router.get("/{game_id}", response_model=schemas.Lobby)
async def get_lobby(game_id: str, *, redis: Redis = Depends(deps.get_redis)):
    return await service.lobby.get(redis, game_id)


@router.post("/join", response_model=schemas.ConnectedToLobby)
async def join_lobby(*, redis: Redis = Depends(deps.get_redis), join_request: schemas.JoinRequest):
    game_id = await service.lobby.get_id_from_join_code(redis, join_request.join_code.upper())
    if game_id is None:
        raise HTTPException(status_code=404, detail="Game not found")

    lobby = await service.lobby.get(redis, game_id)
    joined_player = None

    if join_request.player_id is not None:
        try:
            joined_player = await service.player.get(redis, lobby.id, join_request.player_id)
        except HTTPException as error:
            if error.status_code != 404:
                raise

    if joined_player is None:
        if lobby.state != schemas.lobby.GameState.WAITING_FOR_PLAYERS:
            raise HTTPException(status_code=403, detail="Game already started")
        joined_player = await service.player.create(
            redis,
            join_request=join_request,
            game_id=game_id,
        )

    return schemas.ConnectedToLobby(player=joined_player, lobby=lobby)


@router.post("/create", response_model=schemas.Lobby)
async def create_lobby(
    *,
    redis: Redis = Depends(deps.get_redis),
    current_user=Depends(deps.get_current_user_optional),
    create_game: schemas.CreateGame = schemas.CreateGame(),
):
    return await service.lobby.create(redis, create_game, current_user)
