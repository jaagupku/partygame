import { writable } from 'svelte/store';

export function createGameStore(initialState: Lobby) {
    const lobby = writable(initialState);

    function playerConnected(player_id: string) {
        lobby.update(state => {
            for (const player of state.players) {
                if (player.id !== player_id) {
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

    function playerDisconnected(player_id: string) {
        lobby.update(state => {
            for (const player of state.players) {
                if (player.id !== player_id) {
                    continue;
                }
                player.status = 'disconnected';
            }
            return state;
        });
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
        }
    }

    return {
        ...lobby,
        onMessage,
    }
}