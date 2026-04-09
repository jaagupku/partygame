import { writable } from 'svelte/store';

export function createControllerStore(initialState: ControllerState, onKick: CallableFunction) {
	const controller = writable(initialState);

	function setHost(playerId: string) {
		controller.update((state) => {
			state.isHost = playerId === state.id;
			return state;
		});
	}

	function updateComponent(event: ComponentStateUpdatedEvent) {
		controller.update((state) => {
			if (event.state.type_ === 'display_text_image') {
				state.questionText = String(event.state.props?.text ?? '');
				const image = event.state.props?.image;
				state.questionImage = typeof image === 'string' ? image : undefined;
			}
			if (event.state.type_ === 'player_input') {
				state.activeInputComponentId = event.component_id;
				const kind = String(event.state.props?.kind ?? 'text').toLowerCase();
				if (kind === 'number' || kind === 'ordering') {
					state.inputKind = kind;
				} else {
					state.inputKind = 'text';
				}
			}
			return state;
		});
	}

	function onMessage(msg: string) {
		const messageData = JSON.parse(msg);
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
				controller.update((state) => {
					state.gameState = 'running';
					return state;
				});
				break;
			}
			case 'step_advanced': {
				const event: StepAdvancedEvent = messageData;
				controller.update((state) => {
					state.currentStep = event.step_index;
					return state;
				});
				break;
			}
			case 'component_state_updated': {
				const event: ComponentStateUpdatedEvent = messageData;
				updateComponent(event);
				break;
			}
		}
	}

	return {
		...controller,
		setHost,
		onMessage
	};
}
