class GameKeyFactory:
    @staticmethod
    def game_keys(game_id: str) -> str:
        return f"game:{game_id}:keys"

    @staticmethod
    def game_meta(game_id: str) -> str:
        return f"game:{game_id}:meta"

    @staticmethod
    def game_scores(game_id: str) -> str:
        return f"game:{game_id}:scores"

    @staticmethod
    def game_player(game_id: str, player_id: str) -> str:
        return f"game:{game_id}:players:{player_id}"

    @staticmethod
    def game_component(game_id: str, component_id: str) -> str:
        return f"game:{game_id}:components:{component_id}"

    @staticmethod
    def game_steps(game_id: str) -> str:
        return f"game:{game_id}:steps"

    @staticmethod
    def host_channel(game_id: str) -> str:
        return f"game:{game_id}:channels:host"

    @staticmethod
    def display_channel(game_id: str) -> str:
        return f"game:{game_id}:channels:display"

    @staticmethod
    def player_channel(game_id: str, player_id: str) -> str:
        return f"game:{game_id}:channels:player:{player_id}"

    @staticmethod
    def join_code(join_code: str) -> str:
        return f"join:{join_code}"
