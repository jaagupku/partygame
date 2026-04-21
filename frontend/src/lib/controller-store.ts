import { writable } from 'svelte/store';
import { applyControllerPatch, applyControllerSnapshot } from '$lib/runtime-sync.js';

export function createControllerStore(initialState: ControllerState, onKick: CallableFunction) {
	const controller = writable(initialState);

	function setHost(playerId: string) {
		controller.update((state) => {
			state.isHost = playerId === state.id;
			return state;
		});
	}

	function applySnapshot(event: RuntimeSnapshotEvent) {
		controller.update((state) => {
			applyControllerSnapshot(state, event);
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
			case 'runtime_snapshot': {
				applySnapshot(messageData as RuntimeSnapshotEvent);
				return 'snapshot_applied';
			}
			case 'runtime_patch': {
				let applied = true;
				controller.update((state) => {
					applied = applyControllerPatch(state, messageData as RuntimePatchEvent);
					return state;
				});
				return applied ? 'ok' : 'resync_required';
			}
			case 'player_reaction': {
				const event: PlayerReactionEvent = messageData;
				controller.update((state) => {
					state.lastReaction = event;
					return state;
				});
				break;
			}
			case 'buzzer_state': {
				const event: BuzzerStateEvent = messageData;
				controller.update((state) => {
					state.buzzerActive = event.active;
					state.lobbyPhase = event.active ? 'question_active' : 'host_review';
					if (event.active) {
						state.buzzedPlayerId = undefined;
					}
					return state;
				});
				break;
			}
			case 'buzzer_clicked': {
				const event: BuzzerClickedEvent = messageData;
				controller.update((state) => {
					state.buzzerActive = false;
					state.buzzedPlayerId = event.player_id;
					state.lobbyPhase = 'host_review';
					return state;
				});
				break;
			}
			case 'revealed_submission': {
				const event: RevealedSubmissionEvent = messageData;
				controller.update((state) => {
					state.revealedSubmission = event.submission;
					return state;
				});
				break;
			}
			case 'buzzer_reviewed': {
				const event: BuzzerReviewedEvent = messageData;
				controller.update((state) => {
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

	return {
		...controller,
		setHost,
		onMessage
	};
}
