type ConnectionStatus = "connected" | "disconnected"

type Lobby = {
    id: string;
    join_code: string;
    host_id: string?;
    players: Player[];
};

type Player = {
    id: string;
    name: string;
    game_id: string;
    score: number;
    status: ConnectionStatus;
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

