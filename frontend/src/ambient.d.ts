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
    score: number;
    status: ConnectionStatus;
}

type PlayerJoinedEvent = {
    type_: "player_joined";
    player: Player;
}
