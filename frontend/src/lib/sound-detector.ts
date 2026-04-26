export type SoundCue =
	| 'buzz'
	| 'correct'
	| 'wrong'
	| 'stepOpen'
	| 'answerReveal'
	| 'buzzerArmed'
	| 'timerWarning'
	| 'stepClosed'
	| 'submissionReceived'
	| 'pendingReviewCleared'
	| 'scoreboardShown'
	| 'finaleReveal'
	| 'finaleStage'
	| 'winnerPodium';

export type RuntimeLikeState = {
	activeStep?: {
		id: string;
		input_kind?: string;
		input_enabled?: boolean;
		timer?: {
			ends_at?: number | null;
			remaining_seconds?: number | null;
		};
	} | null;
	displayPhase?: string;
	scoreboardVisible?: boolean;
	buzzerActive?: boolean;
	submissionCount?: number;
	pendingReviewCount?: number;
	endGame?: {
		revealed?: boolean;
		sequence_stage?: string;
	} | null;
	phase?: string;
	lobbyPhase?: string;
};

export type RuntimeEvent =
	| { type_: 'buzzer_clicked'; player_id: string }
	| { type_: 'buzzer_reviewed'; player_id: string; accepted: boolean }
	| {
			type_: 'answer_judged';
			player_id: string;
			accepted: boolean;
			source: 'host_review' | 'auto_evaluation';
			input_kind: string;
			batch_id: string;
			batch_index: number;
			batch_size: number;
	  }
	| { type_: 'scores_updated'; updates: Record<string, number> }
	| { type_: 'update_score'; player_id: string; add_score?: number; set_score?: number }
	| { type_: string };

type NormalizedState = {
	stepId: string | null;
	inputKind: string;
	inputEnabled: boolean;
	displayPhase: string;
	scoreboardVisible: boolean;
	buzzerActive: boolean;
	submissionCount: number;
	pendingReviewCount: number;
	endGameRevealed: boolean;
	endGameStage: string | null;
	phase: string;
	timerEndsAt: number | null;
	timerRemainingSeconds: number | null;
};

interface SyncOptions {
	baseline?: boolean;
	suppressCues?: boolean;
}

interface DetectorOptions {
	timerWarningSeconds?: number;
}

type JudgedBatchState = {
	hasAccepted: boolean;
	hasRejected: boolean;
	remaining: number;
};

export function normalizeSoundState(state?: RuntimeLikeState | null): NormalizedState {
	const activeStep = state?.activeStep ?? null;
	return {
		stepId: activeStep?.id ?? null,
		inputKind: activeStep?.input_kind ?? 'none',
		inputEnabled: Boolean(activeStep?.input_enabled),
		displayPhase: state?.displayPhase ?? 'question_active',
		scoreboardVisible: Boolean(state?.scoreboardVisible),
		buzzerActive: Boolean(state?.buzzerActive),
		submissionCount: state?.submissionCount ?? 0,
		pendingReviewCount: state?.pendingReviewCount ?? 0,
		endGameRevealed: Boolean(state?.endGame?.revealed),
		endGameStage: state?.endGame?.sequence_stage ?? null,
		phase: state?.phase ?? state?.lobbyPhase ?? 'waiting',
		timerEndsAt: activeStep?.timer?.ends_at ?? null,
		timerRemainingSeconds: activeStep?.timer?.remaining_seconds ?? null
	};
}

export function createSoundDetector({ timerWarningSeconds = 3 }: DetectorOptions = {}) {
	let initialized = false;
	let currentState = normalizeSoundState();
	let timerWarningStepId: string | null = null;
	let timerWarningRemainingSecond: number | null = null;
	let timerExpiredStepId: string | null = null;
	const judgedBatches = new Map<string, JudgedBatchState>();

	function currentRemainingSeconds(state: NormalizedState, nowMs = Date.now()): number | null {
		if (!state.stepId || !state.inputEnabled || state.displayPhase === 'answer_reveal') {
			return null;
		}
		if (state.timerEndsAt !== null) {
			return state.timerEndsAt - nowMs / 1000;
		}
		return state.timerRemainingSeconds;
	}

	function resetTimerMarkers(state: NormalizedState, nowMs = Date.now()) {
		const remaining = currentRemainingSeconds(state, nowMs);
		if (!state.stepId) {
			timerWarningStepId = null;
			timerWarningRemainingSecond = null;
			timerExpiredStepId = null;
			return;
		}
		if (remaining !== null && remaining <= timerWarningSeconds && remaining > 0) {
			timerWarningStepId = state.stepId;
			timerWarningRemainingSecond = Math.ceil(remaining);
		} else {
			timerWarningStepId = null;
			timerWarningRemainingSecond = null;
		}
		timerExpiredStepId = remaining !== null && remaining <= 0 ? state.stepId : null;
	}

	function syncState(nextStateLike?: RuntimeLikeState | null, options: SyncOptions = {}) {
		const { baseline = false, suppressCues = false } = options;
		const nextState = normalizeSoundState(nextStateLike);
		if (!initialized || baseline) {
			initialized = true;
			currentState = nextState;
			resetTimerMarkers(nextState);
			return [] as SoundCue[];
		}

		const previousState = currentState;
		currentState = nextState;

		if (suppressCues) {
			if (nextState.stepId !== previousState.stepId) {
				resetTimerMarkers(nextState);
			}
			return [] as SoundCue[];
		}

		const cues: SoundCue[] = [];

		if (nextState.stepId && nextState.stepId !== previousState.stepId) {
			cues.push('stepOpen');
			timerWarningStepId = null;
			timerWarningRemainingSecond = null;
			timerExpiredStepId = null;
		}
		if (
			previousState.displayPhase !== 'answer_reveal' &&
			nextState.displayPhase === 'answer_reveal'
		) {
			cues.push('answerReveal');
		}
		if (!previousState.buzzerActive && nextState.buzzerActive) {
			cues.push('buzzerArmed');
		}
		if (!previousState.scoreboardVisible && nextState.scoreboardVisible) {
			cues.push('scoreboardShown');
		}
		if (!previousState.endGameRevealed && nextState.endGameRevealed) {
			cues.push('finaleReveal');
		} else if (
			nextState.endGameRevealed &&
			previousState.endGameStage &&
			nextState.endGameStage &&
			previousState.endGameStage !== nextState.endGameStage
		) {
			cues.push(nextState.endGameStage === 'scoreboard' ? 'winnerPodium' : 'finaleStage');
		}
		if (nextState.submissionCount > previousState.submissionCount) {
			cues.push('submissionReceived');
		}
		if (previousState.pendingReviewCount > 0 && nextState.pendingReviewCount === 0) {
			cues.push('pendingReviewCleared');
		}
		if (
			nextState.stepId &&
			nextState.stepId === previousState.stepId &&
			previousState.inputEnabled &&
			!nextState.inputEnabled &&
			nextState.inputKind !== 'buzzer' &&
			nextState.displayPhase !== 'answer_reveal' &&
			timerExpiredStepId !== nextState.stepId
		) {
			cues.push('stepClosed');
			timerExpiredStepId = nextState.stepId;
		}
		if (nextState.stepId !== previousState.stepId) {
			resetTimerMarkers(nextState);
		}
		return cues;
	}

	function handleEvent(event: RuntimeEvent, stateLike?: RuntimeLikeState | null) {
		const state = stateLike ? normalizeSoundState(stateLike) : currentState;
		switch (event.type_) {
			case 'buzzer_clicked':
				return ['buzz'] as SoundCue[];
			case 'buzzer_reviewed': {
				const reviewedEvent = event as Extract<RuntimeEvent, { type_: 'buzzer_reviewed' }>;
				return [reviewedEvent.accepted ? 'correct' : 'wrong'] as SoundCue[];
			}
			case 'answer_judged': {
				const judgedEvent = event as Extract<RuntimeEvent, { type_: 'answer_judged' }>;
				if (judgedEvent.source === 'host_review') {
					return [judgedEvent.accepted ? 'correct' : 'wrong'] as SoundCue[];
				}
				const batch = judgedBatches.get(judgedEvent.batch_id) ?? {
					hasAccepted: false,
					hasRejected: false,
					remaining: judgedEvent.batch_size
				};
				batch.hasAccepted = batch.hasAccepted || judgedEvent.accepted;
				batch.hasRejected = batch.hasRejected || !judgedEvent.accepted;
				batch.remaining -= 1;
				if (batch.remaining > 0) {
					judgedBatches.set(judgedEvent.batch_id, batch);
					return [] as SoundCue[];
				}
				judgedBatches.delete(judgedEvent.batch_id);
				if (batch.hasAccepted) {
					return ['correct'] as SoundCue[];
				}
				if (batch.hasRejected && state.inputKind !== 'buzzer') {
					return ['wrong'] as SoundCue[];
				}
				return [] as SoundCue[];
			}
			case 'scores_updated':
			case 'update_score':
			default:
				return [] as SoundCue[];
		}
	}

	function tick(stateLike?: RuntimeLikeState | null, nowMs = Date.now(), suppressCues = false) {
		const liveState = stateLike ? normalizeSoundState(stateLike) : currentState;
		currentState = liveState;
		if (suppressCues) {
			return [] as SoundCue[];
		}
		const remaining = currentRemainingSeconds(liveState, nowMs);
		if (!liveState.stepId || remaining === null) {
			return [] as SoundCue[];
		}
		const cues: SoundCue[] = [];
		const warningSecond = Math.ceil(remaining);
		if (
			remaining <= timerWarningSeconds &&
			remaining > 0 &&
			(timerWarningStepId !== liveState.stepId || timerWarningRemainingSecond !== warningSecond)
		) {
			cues.push('timerWarning');
			timerWarningStepId = liveState.stepId;
			timerWarningRemainingSecond = warningSecond;
		}
		if (remaining <= 0 && timerExpiredStepId !== liveState.stepId) {
			cues.push('stepClosed');
			timerExpiredStepId = liveState.stepId;
		}
		return cues;
	}

	return {
		syncState,
		handleEvent,
		tick
	};
}
