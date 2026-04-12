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
		}
	}

	return {
		...controller,
		setHost,
		onMessage
	};
}
