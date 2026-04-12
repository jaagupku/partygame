import type { FlatStepItem } from './types';

export type InputKindPresentation = {
	kind: PlayerInputKind;
	label: string;
	description: string;
	icon: string;
	recommendedEvaluation: EvaluationType;
	usesPrompt: boolean;
	usesPlaceholder: boolean;
	usesOptions: boolean;
	usesNumericRange: boolean;
};

export type EvaluationPresentation = {
	type: EvaluationType;
	label: string;
	description: string;
	icon: string;
	requiresAnswer: boolean;
	manualReview: boolean;
};

export type StepTemplateId =
	| 'trivia'
	| 'multiple_choice'
	| 'closest_guess'
	| 'exact_number'
	| 'ordering'
	| 'open_answer'
	| 'host_judged'
	| 'buzzer'
	| 'blank';

export type StepTemplateDefinition = {
	id: StepTemplateId;
	label: string;
	description: string;
	icon: string;
	inputKind: PlayerInputKind;
	evaluationType: EvaluationType;
	prompt?: string;
	placeholder?: string;
	options?: string[];
	timerSeconds?: number;
};

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

export const INPUT_KIND_DETAILS: Record<PlayerInputKind, InputKindPresentation> = {
	text: {
		kind: 'text',
		label: 'Free Text',
		description: 'Players type a written answer in their own words.',
		icon: 'fluent:textbox-16-filled',
		recommendedEvaluation: 'exact_text',
		usesPrompt: true,
		usesPlaceholder: true,
		usesOptions: false,
		usesNumericRange: false
	},
	number: {
		kind: 'number',
		label: 'Number Guess',
		description: 'Players submit a number, either exact or closest wins.',
		icon: 'fluent:target-arrow-16-filled',
		recommendedEvaluation: 'exact_number',
		usesPrompt: true,
		usesPlaceholder: true,
		usesOptions: false,
		usesNumericRange: true
	},
	ordering: {
		kind: 'ordering',
		label: 'Order Items',
		description: 'Players arrange items into the right sequence.',
		icon: 'fluent:arrow-sort-16-filled',
		recommendedEvaluation: 'ordering_match',
		usesPrompt: true,
		usesPlaceholder: false,
		usesOptions: true,
		usesNumericRange: false
	},
	radio: {
		kind: 'radio',
		label: 'Single Choice',
		description: 'Players pick one option from a list.',
		icon: 'fluent:radio-button-16-filled',
		recommendedEvaluation: 'exact_text',
		usesPrompt: true,
		usesPlaceholder: false,
		usesOptions: true,
		usesNumericRange: false
	},
	checkbox: {
		kind: 'checkbox',
		label: 'Multiple Choice',
		description: 'Players can select several options, with optional weighting.',
		icon: 'fluent:checkbox-checked-16-filled',
		recommendedEvaluation: 'multi_select_weighted',
		usesPrompt: true,
		usesPlaceholder: false,
		usesOptions: true,
		usesNumericRange: false
	},
	buzzer: {
		kind: 'buzzer',
		label: 'Buzzer',
		description: 'Players race to buzz in before answering live.',
		icon: 'fluent:hand-wave-16-filled',
		recommendedEvaluation: 'host_judged',
		usesPrompt: true,
		usesPlaceholder: false,
		usesOptions: false,
		usesNumericRange: false
	},
	none: {
		kind: 'none',
		label: 'No Player Input',
		description: 'Use the slide for reveal-only or host-led moments.',
		icon: 'fluent:slide-text-16-filled',
		recommendedEvaluation: 'none',
		usesPrompt: false,
		usesPlaceholder: false,
		usesOptions: false,
		usesNumericRange: false
	}
};

export const EVALUATION_DETAILS: Record<EvaluationType, EvaluationPresentation> = {
	none: {
		type: 'none',
		label: 'No Scoring',
		description: 'Show the question without collecting or grading player answers.',
		icon: 'fluent:circle-off-16-filled',
		requiresAnswer: false,
		manualReview: false
	},
	host_judged: {
		type: 'host_judged',
		label: 'Host Judged',
		description: 'The host decides whether answers are correct during play.',
		icon: 'fluent:person-feedback-16-filled',
		requiresAnswer: false,
		manualReview: true
	},
	exact_text: {
		type: 'exact_text',
		label: 'Exact Match',
		description: 'Players must match the expected answer exactly.',
		icon: 'fluent:checkmark-circle-16-filled',
		requiresAnswer: true,
		manualReview: false
	},
	exact_number: {
		type: 'exact_number',
		label: 'Exact Number',
		description: 'Only the precise numeric answer scores.',
		icon: 'fluent:target-arrow-16-filled',
		requiresAnswer: true,
		manualReview: false
	},
	closest_number: {
		type: 'closest_number',
		label: 'Closest Wins',
		description: 'Nearest number gets the points.',
		icon: 'fluent:target-arrow-16-filled',
		requiresAnswer: true,
		manualReview: false
	},
	ordering_match: {
		type: 'ordering_match',
		label: 'Correct Order',
		description: 'Players score by matching the intended sequence.',
		icon: 'fluent:re-order-16-filled',
		requiresAnswer: true,
		manualReview: false
	},
	multi_select_weighted: {
		type: 'multi_select_weighted',
		label: 'Weighted Choices',
		description: 'Each selected option adds or subtracts points.',
		icon: 'fluent:checkbox-person-16-filled',
		requiresAnswer: true,
		manualReview: false
	}
};

export const STEP_TEMPLATES: StepTemplateDefinition[] = [
	{
		id: 'trivia',
		label: 'Trivia',
		description: 'Classic one-correct-answer multiple-choice question.',
		icon: 'fluent:hat-graduation-16-filled',
		inputKind: 'radio',
		evaluationType: 'exact_text',
		prompt: 'Pick the correct answer',
		options: ['Option 1', 'Option 2', 'Option 3', 'Option 4'],
		timerSeconds: 30
	},
	{
		id: 'multiple_choice',
		label: 'Multiple Choice',
		description: 'Select one or more answers with per-option scoring.',
		icon: 'fluent:checkbox-checked-16-filled',
		inputKind: 'checkbox',
		evaluationType: 'multi_select_weighted',
		prompt: 'Select all that apply',
		options: ['Option 1', 'Option 2', 'Option 3', 'Option 4'],
		timerSeconds: 30
	},
	{
		id: 'closest_guess',
		label: 'Closest Guess',
		description: 'Players estimate a number and nearest answer wins.',
		icon: 'fluent:target-arrow-16-filled',
		inputKind: 'number',
		evaluationType: 'closest_number',
		prompt: 'Enter your best guess',
		placeholder: '0',
		timerSeconds: 30
	},
	{
		id: 'exact_number',
		label: 'Exact Number',
		description: 'Only the exact numeric answer scores.',
		icon: 'fluent:target-arrow-16-filled',
		inputKind: 'number',
		evaluationType: 'exact_number',
		prompt: 'Enter the exact number',
		placeholder: '0',
		timerSeconds: 30
	},
	{
		id: 'ordering',
		label: 'Ordering',
		description: 'Players must arrange items into the correct order.',
		icon: 'fluent:re-order-dots-horizontal-16-filled',
		inputKind: 'ordering',
		evaluationType: 'ordering_match',
		prompt: 'Arrange these in the correct order',
		options: ['Item 1', 'Item 2', 'Item 3'],
		timerSeconds: 45
	},
	{
		id: 'open_answer',
		label: 'Open Answer',
		description: 'Players type a short answer that is checked exactly.',
		icon: 'fluent:textbox-16-filled',
		inputKind: 'text',
		evaluationType: 'exact_text',
		prompt: 'Type your answer',
		placeholder: 'Enter answer',
		timerSeconds: 30
	},
	{
		id: 'host_judged',
		label: 'Host Judged',
		description: 'Collect answers and let the host review them live.',
		icon: 'fluent:person-feedback-16-filled',
		inputKind: 'text',
		evaluationType: 'host_judged',
		prompt: 'Type your answer',
		placeholder: 'Enter answer',
		timerSeconds: 30
	},
	{
		id: 'buzzer',
		label: 'Buzzer',
		description: 'Fastest player buzzes in and answers verbally.',
		icon: 'fluent:hand-wave-16-filled',
		inputKind: 'buzzer',
		evaluationType: 'host_judged',
		prompt: 'Buzz in when ready',
		timerSeconds: 15
	},
	{
		id: 'blank',
		label: 'Blank',
		description: 'Start from a safe default and customize everything yourself.',
		icon: 'fluent:slide-add-16-filled',
		inputKind: 'text',
		evaluationType: 'exact_text',
		prompt: '',
		placeholder: '',
		timerSeconds: 30
	}
];

export const MEDIA_TYPES = ['image', 'audio', 'video'] as const;
export const IMAGE_REVEALS = ['none', 'blur_to_clear', 'blur_circle', 'zoom_out'] as const;

export function createStepFromTemplate(
	roundIndex: number,
	stepIndex: number,
	templateId: StepTemplateId = 'blank'
): StepDefinition {
	const template =
		STEP_TEMPLATES.find((candidate) => candidate.id === templateId) ??
		STEP_TEMPLATES.find((candidate) => candidate.id === 'blank');
	const options = template?.options ? [...template.options] : [];
	let answer: StepDefinition['evaluation']['answer'] = '';
	if (template?.evaluationType === 'ordering_match') {
		answer = [...options];
	} else if (template?.evaluationType === 'multi_select_weighted') {
		answer = buildCheckboxWeightedAnswer(options);
	} else if (template?.evaluationType === 'exact_text' && template?.inputKind === 'radio') {
		answer = options[0] ?? '';
	} else if (
		template?.evaluationType === 'exact_number' ||
		template?.evaluationType === 'closest_number'
	) {
		answer = 0;
	} else if (template?.evaluationType === 'none') {
		answer = null;
	}

	return {
		id: `step_${roundIndex}_${stepIndex}`,
		title: `Step ${stepIndex}`,
		body: '',
		timer: {
			seconds: template?.timerSeconds ?? 30,
			enforced: false
		},
		player_input: {
			kind: template?.inputKind ?? 'text',
			prompt: template?.prompt ?? '',
			placeholder: template?.placeholder ?? '',
			options,
			min_value: undefined,
			max_value: undefined,
			step: undefined
		},
		evaluation: {
			type_: template?.evaluationType ?? 'exact_text',
			points: 1,
			answer
		},
		host_behavior: {
			reveal_answers: true,
			show_submissions: true,
			allow_custom_points: true
		}
	};
}

export function getEvaluationDetailsForInputKind(kind: PlayerInputKind): EvaluationPresentation[] {
	return INPUT_KIND_EVALUATIONS[kind].map((type) => EVALUATION_DETAILS[type]);
}

export type StepHealthIssue = {
	id: string;
	label: string;
	icon: string;
};

export function getStepHealthIssues(step: StepDefinition): StepHealthIssue[] {
	const issues: StepHealthIssue[] = [];

	if (!step.title.trim()) {
		issues.push({
			id: 'missing-title',
			label: 'Title missing',
			icon: 'fluent:textbox-16-filled'
		});
	}

	if (
		['ordering', 'radio', 'checkbox'].includes(step.player_input.kind) &&
		step.player_input.options.filter((option) => option.trim()).length < 2
	) {
		issues.push({
			id: 'missing-options',
			label: 'Needs at least 2 options',
			icon: 'fluent:list-16-filled'
		});
	}

	const evaluationDetails = EVALUATION_DETAILS[step.evaluation.type_];
	const hasAnswer = Array.isArray(step.evaluation.answer)
		? step.evaluation.answer.some((value) => String(value).trim())
		: isCheckboxWeightedAnswer(step.evaluation.answer)
			? step.evaluation.answer.option_scores.length > 0
			: String(step.evaluation.answer ?? '').trim().length > 0;
	if (evaluationDetails.requiresAnswer && !hasAnswer) {
		issues.push({
			id: 'missing-answer',
			label: 'Correct answer missing',
			icon: 'fluent:checkmark-circle-warning-16-filled'
		});
	}

	if (step.media && !step.media.src.trim()) {
		issues.push({
			id: 'missing-media',
			label: 'Media source missing',
			icon: 'fluent:image-16-filled'
		});
	}

	if (step.timer.seconds === undefined || step.timer.seconds === null) {
		issues.push({
			id: 'missing-timer',
			label: 'Timer not set',
			icon: 'fluent:timer-off-16-filled'
		});
	}

	return issues;
}

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
					loop: step.media.loop,
					reveal_state: step.media.reveal === 'none' ? 'idle' : 'running',
					reveal_elapsed_seconds: 0,
					reveal_started_at: Date.now() / 1000,
					reveal_duration_seconds: step.timer.seconds ?? 14
				}
			: undefined,
		timer: {
			seconds: step.timer.seconds,
			enforced: step.timer.enforced,
			started_at: Date.now() / 1000,
			ends_at: step.timer.seconds ? Date.now() / 1000 + step.timer.seconds : undefined,
			remaining_seconds: step.timer.seconds
		}
	};
}
