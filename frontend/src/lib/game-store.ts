import { writable } from 'svelte/store';
import { Sound } from 'svelte-sound';
import correctWav from '$lib/assets/sounds/correct.wav';
import wrongWav from '$lib/assets/sounds/wrong.wav';

const correctSound = new Sound(correctWav);
const wrongSound = new Sound(wrongWav);

export function createGameStore(initialState: Lobby) {
	const initial: HostGameState = {
		...initialState,
		activeStep: undefined,
		buzzerActive: false,
		buzzedPlayerId: undefined,
		submissionCount: 0,
		pendingReviewCount: 0,
		revealedSubmission: undefined
	};

	const lobby = writable(initial);

	function setHost(playerId: string) {
		lobby.update((state) => {
			for (const player of state.players) {
				player.isHost = player.id === playerId;
			}
			state.host_id = playerId;
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
				} else if (player.score > score) {
					wrongSound.play();
				}
				player.score = score;
			}
			return state;
		});
	}

	function applySnapshot(event: RuntimeSnapshotEvent) {
		lobby.update((state) => {
			state.state = event.lobby.state;
			state.phase = event.lobby.phase;
			state.current_step = event.lobby.current_step;
			state.host_enabled = event.lobby.host_enabled;
			state.host_id = event.lobby.host_id;
			state.activeStep = event.active_step;
			state.buzzerActive = event.buzzer_active;
			state.buzzedPlayerId = event.buzzed_player_id;
			state.submissionCount = event.submission_count;
			state.pendingReviewCount = event.pending_review_count;
			state.revealedSubmission = event.revealed_submission;
			for (const player of state.players) {
				player.isHost = player.id === state.host_id;
			}
			return state;
		});
	}

	function onMessage(msg: string) {
		const messageData = JSON.parse(msg);
		switch (messageData.type_) {
			case 'player_joined': {
				const event: PlayerJoinedEvent = messageData;
				lobby.update((state) => {
					state.players = [...state.players, event.player];
					return state;
				});
				break;
			}
			case 'player_connected': {
				const event: PlayerConnectedEvent = messageData;
				lobby.update((state) => {
					for (const player of state.players) {
						if (player.id === event.player_id) {
							player.status = 'connected';
						}
					}
					return state;
				});
				break;
			}
			case 'player_disconnected': {
				const event: PlayerDisconnectedEvent = messageData;
				lobby.update((state) => {
					for (const player of state.players) {
						if (player.id === event.player_id) {
							player.status = 'disconnected';
						}
					}
					return state;
				});
				break;
			}
			case 'set_host': {
				const event: SetHostEvent = messageData;
				setHost(event.player_id);
				break;
			}
			case 'kick_player': {
				const event: KickPlayerEvent = messageData;
				lobby.update((state) => {
					state.players = state.players.filter((player) => player.id !== event.player_id);
					return state;
				});
				break;
			}
			case 'runtime_snapshot': {
				applySnapshot(messageData as RuntimeSnapshotEvent);
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
