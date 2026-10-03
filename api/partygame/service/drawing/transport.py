from uuid import uuid4

from pydantic import ValidationError

from partygame.schemas.drawing_game import DrawingCommand
from partygame.service.drawing.runtime import DrawingError, DrawingRuntime


async def process_command(controller, data):
    data = {k: v for k, v in data.items() if k != "player_id"}
    runtime = DrawingRuntime(controller.repo)
    if data.get("type_") == "start_game":
        data = {
            "type_": "drawing_command",
            "action": "start",
            "run_id": data.get("run_id", ""),
            "request_id": uuid4().hex,
        }
    response = {
        "type_": "drawing_ack",
        "request_id": data.get("request_id"),
        "run_id": controller.lobby.run_id or controller.lobby.id,
    }
    try:
        command = DrawingCommand.model_validate(data)
        async with controller.repo.mutation_lock(controller.lobby.id):
            await controller.refresh_lobby()
            revision = await runtime.command(controller.lobby, controller.player.id, command)
        response.update(status="ok", revision=revision)
    except (ValidationError, DrawingError) as error:
        response.update(
            status="error",
            reason=str(error) if isinstance(error, DrawingError) else "invalid_submission",
        )
    if response["status"] == "error":
        state = await runtime.load(controller.lobby)
        response["view"] = runtime.view(state, controller.player.id).model_dump() if state else None
    await controller.send(response)
    # A rejection includes authoritative private state, allowing safe recovery.
    if response["status"] == "error":
        await controller.send(await runtime.snapshot(controller.lobby))
