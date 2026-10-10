export type WaitingAction = 'answer' | 'vote' | 'buzzer' | 'ready' | 'continue' | 'write' | 'draw';

const DRAWING_ACTIONS: Partial<Record<DrawingGameView['phase'], WaitingAction>> = {
	writing: 'write',
	drawing: 'draw',
	voting: 'vote'
};

export function waitingPlayers(state: HostGameState): {
	key: string;
	action?: WaitingAction;
	players: Player[];
} {
	const step = state.activeStep;
	const empty = { key: '', players: [] };
	const drawing = state.drawingGame;
	if (drawing) {
		const action = DRAWING_ACTIONS[drawing.phase];
		if (state.state !== 'running' || state.endGame || !action) return empty;
		const waiting = new Set(drawing.waiting_ids ?? []);
		return {
			key: `${state.run_id ?? state.id}:drawing:${drawing.phase_id}`,
			action,
			players: state.players.filter((p) => waiting.has(p.id) && p.status === 'connected')
		};
	}
	if (
		state.state !== 'running' ||
		state.reviewingHistory ||
		state.endGame ||
		state.activeItem?.type_ === 'round_intro' ||
		!step
	)
		return empty;

	let action: WaitingAction;
	let eligible = state.players.filter((p) => p.id !== state.host_id && p.status === 'connected');
	if (
		!state.host_enabled &&
		state.phase === 'step_complete' &&
		state.displayPhase === 'answer_reveal' &&
		step.price_mode &&
		(state.priceRevealRemainingSeconds ?? 0) > 0
	) {
		action = 'ready';
		eligible = eligible.filter((p) => !state.priceReadyPlayerIds.includes(p.id));
	} else if (state.phase === 'question_active' && step.input_enabled) {
		if (state.displayPhase === 'drawing_vote') {
			action = 'vote';
			eligible = eligible.filter(
				(p) =>
					state.submittedPlayerIds.includes(p.id) &&
					!(state.drawingVotedPlayerIds ?? []).includes(p.id)
			);
		} else if (state.displayPhase !== 'question_active') {
			return empty;
		} else if (step.input_kind === 'buzzer') {
			if (!state.buzzerActive) return empty;
			action = 'buzzer';
			eligible = eligible.filter((p) => !state.disabledBuzzerPlayerIds.includes(p.id));
		} else if (step.input_kind === 'none') {
			if (state.host_enabled || step.evaluation_type !== 'none') return empty;
			action = 'continue';
			eligible = eligible.filter((p) => p.id === state.starter_id);
		} else {
			action = 'answer';
			eligible = eligible.filter((p) => !state.submittedPlayerIds.includes(p.id));
		}
	} else return empty;

	return {
		key: `${state.run_id ?? state.id}:${state.current_step}:${step.id}:${step.timer.started_at ?? ''}:${action}`,
		action,
		players: eligible
	};
}
