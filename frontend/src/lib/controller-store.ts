import { writable } from 'svelte/store';

export function createControllerStore(initialState: ControllerState, onKick: CallableFunction) {
    const controller = writable(initialState);

    function setHost(playerId: string) {
        controller.update(state => {
            state.isHost = playerId === state.id;
            return state;
        });
    }

    function onMessage(msg: string) {
        const messageData = JSON.parse(msg);
        console.log(messageData);
        switch (messageData.type_) {
            case 'set_host': {
                const event: SetHostEvent = messageData;
                setHost(event.player_id);
                break;
            }
            case 'kick_player': {
                onKick();
                break;
            }
            case 'start_game': {
                controller.update(state => {
                    state.gameState = "running";
                    return state;
                });
                break;
            }
        }
    }

    return {
        ...controller,
        setHost,
        onMessage,
    }
}
