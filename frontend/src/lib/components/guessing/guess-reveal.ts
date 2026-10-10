/** Rank by distance before rounded points; keep missing answers last and ties stable. */
export function rankGuessResults(
	results: PriceResult[],
	guess: boolean,
	distance: (answer: unknown) => number
): PriceResult[] {
	const answered = (result: PriceResult) => result.answer !== null && result.answer !== undefined;
	return [...results].sort((a, b) => {
		if (answered(a) !== answered(b)) return answered(a) ? -1 : 1;
		if (guess && answered(a)) {
			const difference = distance(a.answer) - distance(b.answer);
			if (Number.isFinite(difference) && difference !== 0) return difference;
		}
		return b.points - a.points;
	});
}

/** Keep the entire sequence under two seconds, even for a large lobby. */
export function resultDelay(index: number, count: number): number {
	return 450 + index * Math.min(180, 1200 / Math.max(1, count - 1));
}

/** Matches the generator's `max(range(2), key=...)`: the first highest value wins a tie. */
export function choiceWinner(items: { id: string; value: number }[]): string | undefined {
	let winner: { id: string; value: number } | undefined;
	for (const item of items) if (!winner || item.value > winner.value) winner = item;
	return winner?.id;
}

/** Group compare answers by chosen product; unanswered or unknown choices stay in the pool. */
export function choiceTrays(results: PriceResult[], productIds: string[]) {
	const trays = new Map<string, PriceResult[]>(productIds.map((id) => [id, []]));
	const pool: PriceResult[] = [];
	for (const result of results) {
		const tray =
			result.answer === null || result.answer === undefined
				? undefined
				: trays.get(String(result.answer));
		if (tray) tray.push(result);
		else pool.push(result);
	}
	return { trays, pool };
}

/** The lineup pops in, then players hop to their choice one at a time. */
export const CHOICE_INTRO_MS = 500;
const CHOICE_OUTRO_MS = 350;

/** One hop plus a short beat; large lobbies share a fixed budget so the reveal stays brisk. */
export function choiceStepMs(movers: number): number {
	return Math.min(520, 4200 / Math.max(1, movers));
}

export function choiceHopMs(movers: number): number {
	return Math.max(220, Math.min(400, choiceStepMs(movers) - 120));
}

/** The winner is marked after the last hop lands; list rows start after it. */
export function choiceRevealMs(results: PriceResult[], productIds: string[]): number {
	const movers = results.length - choiceTrays(results, productIds).pool.length;
	if (!movers) return CHOICE_INTRO_MS;
	return (
		CHOICE_INTRO_MS + (movers - 1) * choiceStepMs(movers) + choiceHopMs(movers) + CHOICE_OUTRO_MS
	);
}

/** The correct number holds at zero under the reveal sting, then counts up. */
export const COUNT_UP_DELAY_MS = 500;
export const COUNT_UP_MS = 1200;

/** Ease-in (t³), matching the generated `count` sound's accelerating ticks. */
export function countUpValue(target: number, elapsedMs: number): number {
	const t = Math.min(1, Math.max(0, (elapsedMs - COUNT_UP_DELAY_MS) / COUNT_UP_MS));
	return Math.round(target * t ** 3);
}
