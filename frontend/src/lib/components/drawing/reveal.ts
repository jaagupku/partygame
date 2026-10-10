const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

/** Fixed server stage lengths before each vote; the vote keeps its full configured time. */
export const INTRO_SECONDS = { showcase: 4, criterion_reveal: 2 } as const;
export type IntroPhase = keyof typeof INTRO_SECONDS;
export const isIntroPhase = (phase: string): phase is IntroPhase => phase in INTRO_SECONDS;

/** Seconds left in the current stage, measured on the server clock so screens agree. */
export function serverRemaining(view: DrawingGameView): number {
	if (view.paused) return view.remaining_seconds ?? 0;
	if (view.deadline == null) return 0;
	return Math.max(0, view.deadline - (view.server_time ?? Date.now() / 1000));
}

export function revealElapsed(view: DrawingGameView): number {
	if (view.reveal_duration == null || view.server_time == null) return Infinity;
	const remaining = view.paused
		? (view.remaining_seconds ?? 0)
		: (view.deadline ?? view.server_time) - view.server_time;
	return clamp(view.reveal_duration - remaining, 0, view.reveal_duration);
}

export function revealStep(elapsed: number, duration: number, reducedMotion = false) {
	const pointsAt = duration - 8.5;
	const bonusesAt = duration - 6.5;
	return {
		stage:
			elapsed < 1.5
				? ('revealArtists' as const)
				: elapsed < pointsAt
					? ('revealVotes' as const)
					: elapsed < bonusesAt
						? ('revealPoints' as const)
						: elapsed < duration - 5
							? ('revealBonuses' as const)
							: ('revealSummary' as const),
		pointsVisible: elapsed >= pointsAt,
		pointsProgress: reducedMotion
			? Number(elapsed >= pointsAt)
			: 1 - Math.pow(1 - clamp((elapsed - pointsAt) / 2, 0, 1), 3),
		bonusesVisible: elapsed >= bonusesAt
	};
}

// At most twelve waves. All names remain visible, even in a 64-player game.
export function voteStartsAt(index: number, count: number, duration: number): number {
	const batchSize = Math.max(1, Math.ceil(count / 12));
	const waves = Math.ceil(count / batchSize);
	return 1.5 + (Math.floor(index / batchSize) / Math.max(1, waves)) * (duration - 10 - 0.35);
}

/**
 * Which drawing players should be on, from the whole-second countdown: the drawing phase
 * budgets `drawing_seconds` per drawing. Null outside a paced drawing phase.
 */
export function drawingSegment(
	view: DrawingGameView,
	secondsLeft: number
): { index: number; count: number; into: number } | null {
	const count = view.drawing_count ?? 0;
	const each = view.drawing_seconds ?? 0;
	if (view.phase !== 'drawing' || count < 1 || each <= 0) return null;
	const elapsed = count * each - secondsLeft;
	const index = clamp(Math.floor(elapsed / each), 0, count - 1);
	return { index, count, into: elapsed - index * each };
}
