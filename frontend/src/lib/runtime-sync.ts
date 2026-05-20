function withHostFlags(players: Player[], hostId?: string): Player[] {
	return players.map((player) => ({
		...player,
		isHost: player.id === hostId
	}));
}

export function applyHostSnapshot(state: HostGameState, event: RuntimeSnapshotEvent) {
	state.lastRevision = event.revision;
	state.players = withHostFlags(event.players, event.lobby.host_id);
	state.state = event.lobby.state;
	state.phase = event.lobby.phase;
	state.current_step = event.lobby.current_step;
	state.host_enabled = event.lobby.host_enabled;
	state.host_id = event.lobby.host_id;
	state.activeItem = event.active_item ?? undefined;
	state.nextItem = event.next_item ?? undefined;
	state.nextHostAction = event.next_host_action ?? undefined;
	state.activeRound = event.active_round ?? undefined;
	state.activeStep = event.active_step;
	state.displayPhase = event.display_phase;
	state.reviewStepIndex = event.review_step_index;
	state.reviewingHistory = event.reviewing_history;
	state.canReviewPrevious = event.can_review_previous;
	state.canReviewNext = event.can_review_next;
	state.scoreboardVisible = event.scoreboard_visible;
	state.buzzerActive = event.buzzer_active;
	state.buzzedPlayerId = event.buzzed_player_id;
	state.disabledBuzzerPlayerIds = event.disabled_buzzer_player_ids;
	state.submissionCount = event.submission_count;
	state.pendingReviewCount = event.pending_review_count;
	state.drawingItems = event.drawing_items;
	state.ownDrawingId = event.own_drawing_id ?? undefined;
	state.drawingVotedPlayerIds = event.drawing_voted_player_ids;
	state.drawingVoteCount = event.drawing_vote_count;
	state.revealedSubmission = event.revealed_submission;
	state.revealedAnswer = event.revealed_answer;
	state.submissions = event.submissions;
	state.endGame = event.end_game;
}

export function applyHostPatch(state: HostGameState, event: RuntimePatchEvent): boolean {
	if (event.base_revision !== state.lastRevision) {
		return false;
	}

	const { changes } = event;
	if (changes.players !== undefined) {
		state.players =
			changes.lobby && 'host_id' in changes.lobby
				? withHostFlags(changes.players, changes.lobby.host_id)
				: withHostFlags(changes.players, state.host_id);
	}
	if (changes.lobby) {
		if (changes.lobby.state !== undefined) {
			state.state = changes.lobby.state;
		}
		if (changes.lobby.phase !== undefined) {
			state.phase = changes.lobby.phase;
		}
		if (changes.lobby.current_step !== undefined) {
			state.current_step = changes.lobby.current_step;
		}
		if (changes.lobby.host_enabled !== undefined) {
			state.host_enabled = changes.lobby.host_enabled;
		}
		if ('host_id' in changes.lobby) {
			state.host_id = changes.lobby.host_id;
			state.players = withHostFlags(state.players, changes.lobby.host_id);
		}
	}
	if ('active_step' in changes) {
		state.activeStep = changes.active_step;
	}
	if ('active_item' in changes) {
		state.activeItem = changes.active_item ?? undefined;
	}
	if ('next_item' in changes) {
		state.nextItem = changes.next_item ?? undefined;
	}
	if ('next_host_action' in changes) {
		state.nextHostAction = changes.next_host_action ?? undefined;
	}
	if ('active_round' in changes) {
		state.activeRound = changes.active_round ?? undefined;
	}
	if (changes.display_phase !== undefined) {
		state.displayPhase = changes.display_phase;
	}
	if ('review_step_index' in changes) {
		state.reviewStepIndex = changes.review_step_index;
	}
	if (changes.reviewing_history !== undefined) {
		state.reviewingHistory = changes.reviewing_history;
	}
	if (changes.can_review_previous !== undefined) {
		state.canReviewPrevious = changes.can_review_previous;
	}
	if (changes.can_review_next !== undefined) {
		state.canReviewNext = changes.can_review_next;
	}
	if (changes.scoreboard_visible !== undefined) {
		state.scoreboardVisible = changes.scoreboard_visible;
	}
	if (changes.buzzer_active !== undefined) {
		state.buzzerActive = changes.buzzer_active;
	}
	if ('buzzed_player_id' in changes) {
		state.buzzedPlayerId = changes.buzzed_player_id;
	}
	if (changes.disabled_buzzer_player_ids !== undefined) {
		state.disabledBuzzerPlayerIds = changes.disabled_buzzer_player_ids;
	}
	if (changes.submission_count !== undefined) {
		state.submissionCount = changes.submission_count;
	}
	if (changes.pending_review_count !== undefined) {
		state.pendingReviewCount = changes.pending_review_count;
	}
	if (changes.drawing_items !== undefined) {
		state.drawingItems = changes.drawing_items;
	}
	if ('own_drawing_id' in changes) {
		state.ownDrawingId = changes.own_drawing_id ?? undefined;
	}
	if (changes.drawing_voted_player_ids !== undefined) {
		state.drawingVotedPlayerIds = changes.drawing_voted_player_ids;
	}
	if (changes.drawing_vote_count !== undefined) {
		state.drawingVoteCount = changes.drawing_vote_count;
	}
	if ('revealed_submission' in changes) {
		state.revealedSubmission = changes.revealed_submission;
	}
	if ('revealed_answer' in changes) {
		state.revealedAnswer = changes.revealed_answer;
	}
	if ('submissions' in changes) {
		state.submissions = changes.submissions ?? [];
	}
	if ('end_game' in changes) {
		state.endGame = changes.end_game;
	}
	state.lastRevision = event.revision;
	return true;
}

export function applyControllerSnapshot(state: ControllerState, event: RuntimeSnapshotEvent) {
	state.lastRevision = event.revision;
	state.players = withHostFlags(event.players, event.lobby.host_id);
	state.gameState = event.lobby.state;
	state.lobbyPhase = event.lobby.phase;
	state.currentStep = event.lobby.current_step;
	state.hostEnabled = event.lobby.host_enabled;
	state.starterPlayerId = event.lobby.starter_id;
	state.isHost = event.lobby.host_id === state.id;
	state.activeItem = event.active_item ?? undefined;
	state.nextItem = event.next_item ?? undefined;
	state.nextHostAction = event.next_host_action ?? undefined;
	state.activeRound = event.active_round ?? undefined;
	state.activeStep = event.active_step;
	state.displayPhase = event.display_phase;
	state.reviewStepIndex = event.review_step_index;
	state.reviewingHistory = event.reviewing_history;
	state.canReviewPrevious = event.can_review_previous;
	state.canReviewNext = event.can_review_next;
	state.scoreboardVisible = event.scoreboard_visible;
	state.buzzerActive = event.buzzer_active;
	state.buzzedPlayerId = event.buzzed_player_id;
	state.disabledBuzzerPlayerIds = event.disabled_buzzer_player_ids;
	state.submittedPlayerIds = event.submitted_player_ids;
	state.hasSubmitted = event.submitted_player_ids.includes(state.id);
	state.submissionCount = event.submission_count;
	state.pendingReviewCount = event.pending_review_count;
	state.drawingItems = event.drawing_items;
	state.ownDrawingId = event.own_drawing_id ?? undefined;
	state.drawingVotedPlayerIds = event.drawing_voted_player_ids;
	state.drawingVoteCount = event.drawing_vote_count;
	state.revealedSubmission = event.revealed_submission;
	state.revealedAnswer = event.revealed_answer;
	state.hostAnswer = event.host_answer;
	state.submissions = event.submissions;
	state.endGame = event.end_game;
}

export function applyControllerPatch(state: ControllerState, event: RuntimePatchEvent): boolean {
	if (event.base_revision !== state.lastRevision) {
		return false;
	}

	const { changes } = event;
	if (changes.players !== undefined) {
		const currentHostId = state.players.find((player) => player.isHost)?.id;
		state.players =
			changes.lobby && 'host_id' in changes.lobby
				? withHostFlags(changes.players, changes.lobby.host_id)
				: withHostFlags(changes.players, currentHostId);
	}
	if (changes.lobby) {
		if (changes.lobby.state !== undefined) {
			state.gameState = changes.lobby.state;
		}
		if (changes.lobby.phase !== undefined) {
			state.lobbyPhase = changes.lobby.phase;
		}
		if (changes.lobby.current_step !== undefined) {
			state.currentStep = changes.lobby.current_step;
		}
		if (changes.lobby.host_enabled !== undefined) {
			state.hostEnabled = changes.lobby.host_enabled;
		}
		if ('starter_id' in changes.lobby) {
			state.starterPlayerId = changes.lobby.starter_id;
		}
		if ('host_id' in changes.lobby) {
			state.isHost = changes.lobby.host_id === state.id;
			state.players = withHostFlags(state.players, changes.lobby.host_id);
		}
	}
	if ('active_step' in changes) {
		state.activeStep = changes.active_step;
	}
	if ('active_item' in changes) {
		state.activeItem = changes.active_item ?? undefined;
	}
	if ('next_item' in changes) {
		state.nextItem = changes.next_item ?? undefined;
	}
	if ('next_host_action' in changes) {
		state.nextHostAction = changes.next_host_action ?? undefined;
	}
	if ('active_round' in changes) {
		state.activeRound = changes.active_round ?? undefined;
	}
	if (changes.display_phase !== undefined) {
		state.displayPhase = changes.display_phase;
	}
	if ('review_step_index' in changes) {
		state.reviewStepIndex = changes.review_step_index;
	}
	if (changes.reviewing_history !== undefined) {
		state.reviewingHistory = changes.reviewing_history;
	}
	if (changes.can_review_previous !== undefined) {
		state.canReviewPrevious = changes.can_review_previous;
	}
	if (changes.can_review_next !== undefined) {
		state.canReviewNext = changes.can_review_next;
	}
	if (changes.scoreboard_visible !== undefined) {
		state.scoreboardVisible = changes.scoreboard_visible;
	}
	if (changes.buzzer_active !== undefined) {
		state.buzzerActive = changes.buzzer_active;
	}
	if ('buzzed_player_id' in changes) {
		state.buzzedPlayerId = changes.buzzed_player_id;
	}
	if (changes.disabled_buzzer_player_ids !== undefined) {
		state.disabledBuzzerPlayerIds = changes.disabled_buzzer_player_ids;
	}
	if (changes.submitted_player_ids !== undefined) {
		state.submittedPlayerIds = changes.submitted_player_ids;
		state.hasSubmitted = changes.submitted_player_ids.includes(state.id);
	}
	if (changes.submission_count !== undefined) {
		state.submissionCount = changes.submission_count;
	}
	if (changes.pending_review_count !== undefined) {
		state.pendingReviewCount = changes.pending_review_count;
	}
	if (changes.drawing_items !== undefined) {
		state.drawingItems = changes.drawing_items;
	}
	if ('own_drawing_id' in changes) {
		state.ownDrawingId = changes.own_drawing_id ?? undefined;
	}
	if (changes.drawing_voted_player_ids !== undefined) {
		state.drawingVotedPlayerIds = changes.drawing_voted_player_ids;
	}
	if (changes.drawing_vote_count !== undefined) {
		state.drawingVoteCount = changes.drawing_vote_count;
	}
	if ('revealed_submission' in changes) {
		state.revealedSubmission = changes.revealed_submission;
	}
	if ('revealed_answer' in changes) {
		state.revealedAnswer = changes.revealed_answer;
	}
	if ('host_answer' in changes) {
		state.hostAnswer = changes.host_answer;
	}
	if (changes.submissions !== undefined) {
		state.submissions = changes.submissions;
	}
	if ('end_game' in changes) {
		state.endGame = changes.end_game;
	}
	state.lastRevision = event.revision;
	return true;
}
