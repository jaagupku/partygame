import { writable } from 'svelte/store';
import { Sound } from 'svelte-sound';
import correctWav from '$lib/assets/sounds/correct.wav';
import wrongWav from '$lib/assets/sounds/wrong.wav';

const correctSound = new Sound(correctWav);
const wrongSound = new Sound(wrongWav);

type HostGameState = Lobby & {
	questionText: string;
	questionImage?: string;
	currentStep: number;
	components: Record<string, ComponentRuntimeState>;
};

export function createGameStore(initialState: Lobby) {
	const initial: HostGameState = {
		...initialState,
		questionText: '',
		questionImage: undefined,
		currentStep: initialState.current_step ?? 0,
		components: {}
	};

	const lobby = writable(initial);

	function playerConnected(playerId: string) {
		lobby.update((state) => {
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
		lobby.update((state) => {
			state.players = [...state.players, player];
			return state;
		});
	}

	function playerDisconnected(playerId: string) {
		lobby.update((state) => {
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
		lobby.update((state) => {
			for (const player of state.players) {
				player.isHost = player.id === playerId;
			}
			state.host_id = playerId;
			return state;
		});
	}

	function removePlayer(playerId: string) {
		lobby.update((state) => {
			state.players = state.players.filter((player) => player.id !== playerId);
			return state;
		});
	}

	function updateScore(playerId: string, score: number) {
		lobby.update((state) => {
			for (const player of state.players) {
				if (player.id !== playerId) {
					continue;
				}
				if (player.score < score) {
					correctSound.play();
				} else {
					wrongSound.play();
				}
				player.score = score;
			}
			return state;
		});
	}

	function updateComponentState(event: ComponentStateUpdatedEvent) {
		lobby.update((state) => {
			state.components[event.component_id] = event.state;
			if (event.state.type_ === 'display_text_image') {
				state.questionText = String(event.state.props?.text ?? '');
				const image = event.state.props?.image;
				state.questionImage = typeof image === 'string' ? image : undefined;
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
				lobby.update((state) => {
					state.state = 'running';
					return state;
				});
				break;
			}
			case 'step_advanced': {
				const event: StepAdvancedEvent = messageData;
				lobby.update((state) => {
					state.currentStep = event.step_index;
					return state;
				});
				break;
			}
			case 'component_state_updated': {
				const event: ComponentStateUpdatedEvent = messageData;
				updateComponentState(event);
				break;
			}
			case 'scores_updated': {
				const event: ScoresUpdatedEvent = messageData;
				for (const [playerId, score] of Object.entries(event.updates)) {
					updateScore(playerId, score);
				}
				break;
			}
			case 'update_score': {
				const event: UpdateScoreEvent = messageData;
				if (event.set_score !== undefined) {
					updateScore(event.player_id, event.set_score);
				}
				break;
			}
		}
	}
	if (initialState.host_id) {
		setHost(initialState.host_id);
	}

	return {
		...lobby,
		onMessage
	};
}
