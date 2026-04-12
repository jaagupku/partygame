import { writable } from 'svelte/store';

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
			state.gameState = event.lobby.state;
			state.lobbyPhase = event.lobby.phase;
			state.currentStep = event.lobby.current_step;
			state.hostEnabled = event.lobby.host_enabled;
			state.isHost = event.lobby.host_id === state.id;
			state.activeStep = event.active_step;
			state.displayPhase = event.display_phase;
			state.scoreboardVisible = event.scoreboard_visible;
			state.buzzerActive = event.buzzer_active;
			state.buzzedPlayerId = event.buzzed_player_id;
			state.disabledBuzzerPlayerIds = event.disabled_buzzer_player_ids;
			state.submittedPlayerIds = event.submitted_player_ids;
			state.hasSubmitted = event.submitted_player_ids.includes(state.id);
			state.submissionCount = event.submission_count;
			state.pendingReviewCount = event.pending_review_count;
			state.revealedSubmission = event.revealed_submission;
			state.revealedAnswer = event.revealed_answer;
			state.hostAnswer = event.host_answer;
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
			case 'submissions_updated': {
				const event: SubmissionsUpdatedEvent = messageData;
				controller.update((state) => {
					state.submissions = event.items;
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
	}

	return {
		...controller,
		setHost,
		onMessage
	};
}
