type WeightedOptionScore = {
	option: string;
	points: number;
};

export type RevealedOptionState = {
	option: string;
	correct: boolean;
	points: number;
	pointsLabel: string;
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
	const pointsLabel = formatPointsLabel(entry.points);
	return `${entry.option} (${pointsLabel})`;
}

export function formatPointsLabel(points: number): string {
	return points > 0 ? `+${points}` : String(points);
}

export function isOptionRevealStep(step?: RuntimeStepState): boolean {
	return (
		Boolean(step?.input_options?.length) &&
		((step?.input_kind === 'radio' && step.evaluation_type === 'exact_text') ||
			(step?.input_kind === 'checkbox' && step.evaluation_type === 'multi_select_weighted'))
	);
}

export function isOrderingRevealStep(step?: RuntimeStepState): boolean {
	return Boolean(
		step?.input_options?.length &&
			step.input_kind === 'ordering' &&
			step.evaluation_type === 'ordering_match'
	);
}

export function buildOrderingRevealItems(
	step: RuntimeStepState,
	revealedAnswer?: RevealedAnswer,
	revealed = false
): string[] {
	const availableOptions = [...step.input_options];
	if (!revealed || !Array.isArray(revealedAnswer?.value)) {
		return availableOptions;
	}

	const unusedOptions = [...availableOptions];
	const orderedItems: string[] = [];
	for (const value of revealedAnswer.value) {
		const option = String(value);
		const optionIndex = unusedOptions.indexOf(option);
		if (optionIndex === -1) {
			continue;
		}
		orderedItems.push(unusedOptions.splice(optionIndex, 1)[0]);
	}
	return [...orderedItems, ...unusedOptions];
}

export function buildRevealedOptionStates(
	step: RuntimeStepState,
	revealedAnswer?: RevealedAnswer
): RevealedOptionState[] {
	if (!isOptionRevealStep(step)) {
		return [];
	}

	if (step.input_kind === 'radio') {
		const correctAnswer = String(revealedAnswer?.value ?? '');
		return step.input_options.map((option) => {
			const correct = option === correctAnswer;
			const points = correct ? step.evaluation_points : 0;
			return {
				option,
				correct,
				points,
				pointsLabel: `${formatPointsLabel(points)} pts`
			};
		});
	}

	const optionScores =
		revealedAnswer?.value &&
		typeof revealedAnswer.value === 'object' &&
		'option_scores' in revealedAnswer.value &&
		Array.isArray(revealedAnswer.value.option_scores)
			? revealedAnswer.value.option_scores.filter(isWeightedOptionScore)
			: [];
	const pointsByOption = new Map(optionScores.map((entry) => [entry.option, entry.points]));

	return step.input_options.map((option) => {
		const points = pointsByOption.get(option) ?? 0;
		return {
			option,
			correct: points > 0,
			points,
			pointsLabel: `${formatPointsLabel(points)} pts`
		};
	});
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
