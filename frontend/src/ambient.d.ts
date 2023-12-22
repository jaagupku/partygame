type ConnectionStatus = "connected" | "disconnected"
type GameState = "waiting_for_players" | "running" | "paused"

type Lobby = {
    id: string;
    join_code: string;
    host_id: string?;
    players: Player[];
    connection: ConnectionStatus;
    state: GameState;
};

type Player = {
    id: string;
    name: string;
    game_id: string;
    score: number;
    status: ConnectionStatus;
    isHost: boolean?;
}

type ConnectedToLobby = {
    player: Player;
    lobby: Lobby;
}

type PlayerJoinedEvent = {
    type_: "player_joined";
    player: Player;
}

type PlayerConnectedEvent = {
    type_: "player_connected";
    player_id: string;
}

type PlayerDisconnectedEvent = {
    type_: "player_disconnected";
    player_id: string;
}

type SetHostEvent = {
    type_: "set_host";
    player_id: string;
}

type KickPlayerEvent = {
    type_: "kick_player"
    player_id: string;
}

type StartGameEvent = {
    type_: "start_game"
}

type BuzzerStateEvent = {
    type_: "buzzer_state"
    state: "active" | "deactive"
}

type ControllerState = {
    id: string;
    isHost: boolean;
    gameState: GameState;
}
