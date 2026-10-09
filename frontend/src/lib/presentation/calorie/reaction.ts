/** Only public, revealed scores inform the coach; calories never represent exercise targets. */
export function calorieReaction(results: PriceResult[] = [], playerId?: string) {
	if (!playerId) return results.some((result) => result.points >= 800) ? 'close' : 'encourage';
	// Phones also mark any scoring guess as correct, so the coach must not contradict that.
	const points = results.find((result) => result.player_id === playerId)?.points ?? 0;
	return points >= 800 ? 'close' : points > 0 ? 'partial' : 'encourage';
}

const podiumStages: Record<string, number> = { third_place: 3, second_place: 2, first_place: 1 };

/** Final placement is the only public whole-game result. Displays follow the podium stage. */
export function calorieFinaleReaction(place?: number) {
	if (place === undefined) return 'complete';
	return place === 1 ? 'champion' : place <= 3 ? 'podium' : 'keepTraining';
}

export function calorieStageReaction(stage: string) {
	return calorieFinaleReaction(podiumStages[stage]);
}
