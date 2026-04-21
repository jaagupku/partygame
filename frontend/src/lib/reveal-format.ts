type WeightedOptionScore = {
	option: string;
	points: number;
};

function isWeightedOptionScore(entry: unknown): entry is WeightedOptionScore {
	return (
		typeof entry === 'object' &&
		entry !== null &&
		'option' in entry &&
		'points' in entry &&
		typeof entry.option === 'string' &&
		typeof entry.points === 'number'
	);
}

function formatWeightedOptionScore(entry: WeightedOptionScore): string {
	const pointsLabel = entry.points > 0 ? `+${entry.points}` : String(entry.points);
	return `${entry.option} (${pointsLabel})`;
}

export function formatRevealValue(value: unknown): string {
	if (Array.isArray(value)) {
		return value.map((entry) => String(entry)).join(' · ');
	}

	if (
		value &&
		typeof value === 'object' &&
		'option_scores' in value &&
		Array.isArray(value.option_scores)
	) {
		const optionScores = value.option_scores.filter(isWeightedOptionScore);
		if (optionScores.length > 0) {
			return optionScores.map(formatWeightedOptionScore).join(' · ');
		}
	}

	if (value && typeof value === 'object') {
		return JSON.stringify(value);
	}

	return String(value ?? '');
}
