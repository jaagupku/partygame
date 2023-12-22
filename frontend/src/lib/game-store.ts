import { writable } from 'svelte/store';

export function createGameStore(initialState: Lobby) {
    const lobby = writable(initialState);

    function playerConnected(playerId: string) {
        lobby.update(state => {
            for (const player of state.players) {
                if (player.id !== playerId) {
                    continue;
                }
                player.status = 'connected';
            }
            return state;
        });
    }

    function playerJoined(player: Player) {
        lobby.update(state => {
            state.players = [...state.players, player];
            return state;
        });
    }

    function playerDisconnected(playerId: string) {
        lobby.update(state => {
            for (const player of state.players) {
                if (player.id !== playerId) {
                    continue;
                }
                player.status = 'disconnected';
            }
            return state;
        });
    }

    function setHost(playerId: string) {
        lobby.update(state => {
            for (const player of state.players) {
                if (player.id === playerId) {
                    player.isHost = true;
                } else {
                    player.isHost = false;
                }
            }
            state.host_id = playerId;
            return state;
        });
    }

    function removePlayer(playerId: string) {
        lobby.update(state => {
            state.players = state.players.filter(player => player.id !== playerId);
            return state;
        })
    }

    function onMessage(msg: string) {
        const messageData = JSON.parse(msg);
        switch (messageData.type_) {
            case 'player_joined': {
                const event: PlayerJoinedEvent = messageData;
                playerJoined(event.player);
                break;
            }
            case 'player_connected': {
                const event: PlayerConnectedEvent = messageData;
                playerConnected(event.player_id);
                break;
            }
            case 'player_disconnected': {
                const event: PlayerDisconnectedEvent = messageData;
                playerDisconnected(event.player_id);
                break;
            }
            case 'set_host': {
                const event: SetHostEvent = messageData;
                setHost(event.player_id);
                break;
            }
            case 'kick_player': {
                const event: KickPlayerEvent = messageData;
                removePlayer(event.player_id);
                break;
            }
            case 'start_game': {
                lobby.update(state => {
                    state.state = 'running';
                    return state;
                });
                break;
            }
        }
    }
    if (initialState.host_id) {
        setHost(initialState.host_id);
    }

    return {
        ...lobby,
        onMessage,
    }
}