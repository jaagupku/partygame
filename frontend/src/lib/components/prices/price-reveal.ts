/** Rank guesses by actual distance, including answers that received the same rounded score. */
export function rankPriceResults(step: RuntimeStepState): PriceResult[] {
	const price = step.price_reveal?.[0]?.price_minor;
	const distance = (answer: unknown) => {
		const value = Number(answer);
		return price !== undefined && Number.isFinite(value)
			? Math.abs(Math.round(value * 100) - price)
			: Infinity;
	};
	const answered = (result: PriceResult) => result.answer !== null && result.answer !== undefined;
	return [...(step.price_results ?? [])].sort((a, b) => {
		if (answered(a) !== answered(b)) return answered(a) ? -1 : 1;
		if (step.price_mode === 'guess' && answered(a)) {
			const difference = distance(a.answer) - distance(b.answer);
			if (Number.isFinite(difference) && difference !== 0) return difference;
		}
		return b.points - a.points;
	});
}

/** Keep the entire sequence under two seconds, even for a large lobby. */
export function priceResultDelay(index: number, count: number): number {
	return 450 + index * Math.min(180, 1200 / Math.max(1, count - 1));
}
