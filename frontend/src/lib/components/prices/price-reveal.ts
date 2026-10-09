import { rankGuessResults } from '../guessing/guess-reveal';

/** Rank guesses by actual distance, including answers that received the same rounded score. */
export function rankPriceResults(step: RuntimeStepState): PriceResult[] {
	const price = step.price_reveal?.[0]?.price_minor;
	const distance = (answer: unknown) => {
		const value = Number(answer);
		return price !== undefined && Number.isFinite(value)
			? Math.abs(Math.round(value * 100) - price)
			: Infinity;
	};
	return rankGuessResults(step.price_results ?? [], step.price_mode === 'guess', distance);
}
