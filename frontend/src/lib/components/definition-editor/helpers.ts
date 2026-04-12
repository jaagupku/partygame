import type { FlatStepItem } from './types';

export const INPUT_KINDS: PlayerInputKind[] = [
	'none',
	'buzzer',
	'text',
	'number',
	'ordering',
	'radio',
	'checkbox'
];

export const EVALUATION_TYPES: EvaluationType[] = [
	'none',
	'host_judged',
	'exact_text',
	'exact_number',
	'closest_number',
	'ordering_match',
	'multi_select_weighted'
];

export const INPUT_KIND_EVALUATIONS: Record<PlayerInputKind, EvaluationType[]> = {
	none: ['none'],
	buzzer: ['host_judged'],
	text: ['none', 'host_judged', 'exact_text'],
	number: ['none', 'host_judged', 'exact_number', 'closest_number'],
	ordering: ['none', 'host_judged', 'ordering_match'],
	radio: ['none', 'host_judged', 'exact_text'],
	checkbox: ['none', 'host_judged', 'multi_select_weighted']
};

export const DEFAULT_EVALUATION_BY_INPUT_KIND: Record<PlayerInputKind, EvaluationType> = {
	none: 'none',
	buzzer: 'host_judged',
	text: 'exact_text',
	number: 'exact_number',
	ordering: 'ordering_match',
	radio: 'exact_text',
	checkbox: 'multi_select_weighted'
};

export const MEDIA_TYPES = ['image', 'audio', 'video'] as const;
export const IMAGE_REVEALS = ['none', 'blur_to_clear', 'blur_circle', 'zoom_out'] as const;

export function buildFlatSteps(
	definition: GameDefinition,
	getStepKey: (step: StepDefinition) => string
): FlatStepItem[] {
	const items: FlatStepItem[] = [];
	let globalIndex = 0;
	definition.rounds.forEach((round, roundIndex) => {
		round.steps.forEach((step, stepIndex) => {
			items.push({
				roundIndex,
				stepIndex,
				roundId: round.id,
				roundTitle: round.title ?? round.id,
				step,
				stepKey: getStepKey(step),
				stepId: step.id,
				globalIndex
			});
			globalIndex += 1;
		});
	});
	return items;
}

export function stepPreview(step: StepDefinition): string {
	if (step.body?.trim()) {
		return step.body.trim();
	}
	if (step.player_input.prompt?.trim()) {
		return step.player_input.prompt.trim();
	}
	return 'No supporting text yet.';
}

export function stepBadges(step: StepDefinition): string[] {
	const badges = [`${step.player_input.kind}`, `${step.evaluation.type_}`];
	if (step.timer.seconds !== undefined) {
		badges.push(`${step.timer.seconds}s`);
	}
	if (step.media) {
		badges.push(step.media.type_);
	}
	return badges;
}

export function getOrderingAnswer(step: StepDefinition): string[] {
	return Array.isArray(step.evaluation.answer)
		? step.evaluation.answer.map((value) => String(value))
		: [...step.player_input.options];
}

export function isCheckboxWeightedAnswer(answer: unknown): answer is CheckboxWeightedAnswer {
	if (!answer || typeof answer !== 'object' || !('option_scores' in answer)) {
		return false;
	}
	const optionScores = (answer as CheckboxWeightedAnswer).option_scores;
	return (
		Array.isArray(optionScores) && optionScores.every((entry) => typeof entry?.option === 'string')
	);
}

export function buildCheckboxWeightedAnswer(options: string[]): CheckboxWeightedAnswer {
	return {
		option_scores: options.map((option) => ({ option, points: 0 }))
	};
}

export function getCheckboxOptionScores(step: StepDefinition): CheckboxOptionScore[] {
	const entries = isCheckboxWeightedAnswer(step.evaluation.answer)
		? step.evaluation.answer.option_scores
		: [];
	const pointsByOption = new Map(entries.map((entry) => [entry.option, Number(entry.points) || 0]));
	return step.player_input.options.map((option) => ({
		option,
		points: pointsByOption.get(option) ?? 0
	}));
}

export function getTextAnswer(step: StepDefinition): string {
	if (Array.isArray(step.evaluation.answer) || isCheckboxWeightedAnswer(step.evaluation.answer)) {
		return '';
	}
	return String(step.evaluation.answer ?? '');
}

export function getNumberAnswer(step: StepDefinition): number | undefined {
	const value = Number(step.evaluation.answer);
	return Number.isFinite(value) ? value : undefined;
}

export function normalizeAnswer(step: StepDefinition): StepDefinition['evaluation']['answer'] {
	if (step.evaluation.type_ === 'ordering_match') {
		return getOrderingAnswer(step)
			.map((value) => value.trim())
			.filter(Boolean);
	}
	if (step.evaluation.type_ === 'multi_select_weighted') {
		return {
			option_scores: getCheckboxOptionScores(step)
				.map((entry) => ({
					option: entry.option.trim(),
					points: Math.trunc(entry.points)
				}))
				.filter((entry) => entry.option)
		};
	}
	if (step.evaluation.type_ === 'exact_number' || step.evaluation.type_ === 'closest_number') {
		return step.evaluation.answer === '' ? null : Number(step.evaluation.answer);
	}
	const value = getTextAnswer(step).trim();
	return value || null;
}

export function buildRuntimePreviewStep(step: StepDefinition): RuntimeStepState {
	return {
		id: step.id,
		title: step.title,
		body: step.body,
		evaluation_type: step.evaluation.type_,
		evaluation_points: step.evaluation.points,
		input_enabled: true,
		input_kind: step.player_input.kind,
		input_prompt: step.player_input.prompt,
		input_placeholder: step.player_input.placeholder,
		input_options: [...step.player_input.options],
		slider_min: step.player_input.min_value,
		slider_max: step.player_input.max_value,
		slider_step: step.player_input.step,
		media: step.media
			? {
					type_: step.media.type_,
					src: step.media.src,
					reveal: step.media.reveal,
					loop: step.media.loop
				}
			: undefined,
		timer: {
			seconds: step.timer.seconds,
			enforced: step.timer.enforced,
			started_at: Date.now() / 1000,
			ends_at: step.timer.seconds ? Date.now() / 1000 + step.timer.seconds : undefined
		}
	};
}
