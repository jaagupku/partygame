from partygame.state import GameKeyFactory


def test_game_key_factory_shapes():
    game_id = "g1"
    player_id = "p1"
    component_id = "c1"

    assert GameKeyFactory.game_meta(game_id) == "game:g1:meta"
    assert GameKeyFactory.game_scores(game_id) == "game:g1:scores"
    assert GameKeyFactory.game_player(game_id, player_id) == "game:g1:players:p1"
    assert GameKeyFactory.game_component(game_id, component_id) == "game:g1:components:c1"
    assert GameKeyFactory.game_steps(game_id) == "game:g1:steps"
    assert GameKeyFactory.host_channel(game_id) == "game:g1:channels:host"
    assert GameKeyFactory.display_channel(game_id) == "game:g1:channels:display"
    assert GameKeyFactory.player_channel(game_id, player_id) == "game:g1:channels:player:p1"
    assert GameKeyFactory.join_code("ABCDE") == "join:ABCDE"
