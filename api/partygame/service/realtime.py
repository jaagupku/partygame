from __future__ import annotations

from collections import defaultdict
from typing import Any

_display_connections: dict[str, set[Any]] = defaultdict(set)
_player_connections: dict[str, dict[str, Any]] = defaultdict(dict)


def register_display(game_id: str, controller: Any):
    _display_connections[game_id].add(controller)


def unregister_display(game_id: str, controller: Any):
    controllers = _display_connections.get(game_id)
    if controllers is None:
        return
    controllers.discard(controller)
    if not controllers:
        _display_connections.pop(game_id, None)


def register_player(game_id: str, player_id: str, controller: Any):
    _player_connections[game_id][player_id] = controller


def unregister_player(game_id: str, player_id: str, controller: Any):
    players = _player_connections.get(game_id)
    if players is None:
        return
    if players.get(player_id) is controller:
        players.pop(player_id, None)
    if not players:
        _player_connections.pop(game_id, None)


def get_displays(game_id: str) -> list[Any]:
    return list(_display_connections.get(game_id, set()))


def get_players(game_id: str, exclude: set[str] | None = None) -> list[Any]:
    exclude = exclude or set()
    players = _player_connections.get(game_id, {})
    return [controller for player_id, controller in players.items() if player_id not in exclude]
