import { writable } from 'svelte/store';
import { applyHostPatch, applyHostSnapshot } from '$lib/runtime-sync.js';

export function createGameStore(initialState: Lobby) {
	const initial: HostGameState = {
		...initialState,
		lastRevision: 0,
		activeItem: undefined,
		nextItem: undefined,
		nextHostAction: undefined,
		activeStep: undefined,
		activeRound: undefined,
		displayPhase: 'question_active',
		scoreboardVisible: false,
		buzzerActive: false,
		buzzedPlayerId: undefined,
		disabledBuzzerPlayerIds: [],
		submissionCount: 0,
		pendingReviewCount: 0,
		revealedSubmission: undefined,
		revealedAnswer: undefined,
		endGame: undefined,
		lastReaction: undefined
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
				player.score = score;
			}
			return state;
		});
	}

	function applySnapshot(event: RuntimeSnapshotEvent) {
		lobby.update((state) => {
			applyHostSnapshot(state, event);
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
				return 'snapshot_applied';
			}
			case 'runtime_patch': {
				let applied = true;
				lobby.update((state) => {
					applied = applyHostPatch(state, messageData as RuntimePatchEvent);
					return state;
				});
				return applied ? 'ok' : 'resync_required';
			}
			case 'player_reaction': {
				const event: PlayerReactionEvent = messageData;
				lobby.update((state) => {
					state.lastReaction = event;
					return state;
				});
				break;
			}
			case 'buzzer_state': {
				const event: BuzzerStateEvent = messageData;
				lobby.update((state) => {
					state.buzzerActive = event.active;
					state.phase = event.active ? 'question_active' : 'host_review';
					if (event.active) {
						state.buzzedPlayerId = undefined;
					}
					return state;
				});
				break;
			}
			case 'buzzer_clicked': {
				const event: BuzzerClickedEvent = messageData;
				lobby.update((state) => {
					state.buzzerActive = false;
					state.buzzedPlayerId = event.player_id;
					state.phase = 'host_review';
					return state;
				});
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
			case 'buzzer_reviewed': {
				const event: BuzzerReviewedEvent = messageData;
				lobby.update((state) => {
					state.disabledBuzzerPlayerIds = event.disabled_buzzer_player_ids;
					state.buzzedPlayerId = event.accepted ? event.player_id : undefined;
					state.buzzerActive = false;
					return state;
				});
				break;
			}
		}
		return 'ok';
	}

	if (initialState.host_id) {
		setHost(initialState.host_id);
	}

	return {
		...lobby,
		onMessage
	};
}
