import { getMessages, formatSeconds } from '$lib/i18n';
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

export function getInputKindDetails(): Record<PlayerInputKind, InputKindPresentation> {
	const localized = getMessages().editor.inputKinds;
	return {
		text: {
			kind: 'text',
			label: localized.text.label,
			description: localized.text.description,
			icon: 'fluent:textbox-16-filled',
			recommendedEvaluation: 'exact_text',
			usesPrompt: true,
			usesPlaceholder: true,
			usesOptions: false,
			usesNumericRange: false
		},
		number: {
			kind: 'number',
			label: localized.number.label,
			description: localized.number.description,
			icon: 'fluent:target-arrow-16-filled',
			recommendedEvaluation: 'exact_number',
			usesPrompt: true,
			usesPlaceholder: true,
			usesOptions: false,
			usesNumericRange: true
		},
		ordering: {
			kind: 'ordering',
			label: localized.ordering.label,
			description: localized.ordering.description,
			icon: 'fluent:arrow-sort-16-filled',
			recommendedEvaluation: 'ordering_match',
			usesPrompt: true,
			usesPlaceholder: false,
			usesOptions: true,
			usesNumericRange: false
		},
		radio: {
			kind: 'radio',
			label: localized.radio.label,
			description: localized.radio.description,
			icon: 'fluent:radio-button-16-filled',
			recommendedEvaluation: 'exact_text',
			usesPrompt: true,
			usesPlaceholder: false,
			usesOptions: true,
			usesNumericRange: false
		},
		checkbox: {
			kind: 'checkbox',
			label: localized.checkbox.label,
			description: localized.checkbox.description,
			icon: 'fluent:checkbox-checked-16-filled',
			recommendedEvaluation: 'multi_select_weighted',
			usesPrompt: true,
			usesPlaceholder: false,
			usesOptions: true,
			usesNumericRange: false
		},
		buzzer: {
			kind: 'buzzer',
			label: localized.buzzer.label,
			description: localized.buzzer.description,
			icon: 'fluent:hand-wave-16-filled',
			recommendedEvaluation: 'host_judged',
			usesPrompt: true,
			usesPlaceholder: false,
			usesOptions: false,
			usesNumericRange: false
		},
		none: {
			kind: 'none',
			label: localized.none.label,
			description: localized.none.description,
			icon: 'fluent:slide-text-16-filled',
			recommendedEvaluation: 'none',
			usesPrompt: false,
			usesPlaceholder: false,
			usesOptions: false,
			usesNumericRange: false
		}
	};
}

export function getEvaluationDetails(): Record<EvaluationType, EvaluationPresentation> {
	const localized = getMessages().editor.evaluations;
	return {
		none: {
			type: 'none',
			label: localized.none.label,
			description: localized.none.description,
			icon: 'fluent:circle-off-16-filled',
			requiresAnswer: false,
			manualReview: false
		},
		host_judged: {
			type: 'host_judged',
			label: localized.host_judged.label,
			description: localized.host_judged.description,
			icon: 'fluent:person-feedback-16-filled',
			requiresAnswer: false,
			manualReview: true
		},
		exact_text: {
			type: 'exact_text',
			label: localized.exact_text.label,
			description: localized.exact_text.description,
			icon: 'fluent:checkmark-circle-16-filled',
			requiresAnswer: true,
			manualReview: false
		},
		exact_number: {
			type: 'exact_number',
			label: localized.exact_number.label,
			description: localized.exact_number.description,
			icon: 'fluent:target-arrow-16-filled',
			requiresAnswer: true,
			manualReview: false
		},
		closest_number: {
			type: 'closest_number',
			label: localized.closest_number.label,
			description: localized.closest_number.description,
			icon: 'fluent:target-arrow-16-filled',
			requiresAnswer: true,
			manualReview: false
		},
		ordering_match: {
			type: 'ordering_match',
			label: localized.ordering_match.label,
			description: localized.ordering_match.description,
			icon: 'fluent:re-order-16-filled',
			requiresAnswer: true,
			manualReview: false
		},
		multi_select_weighted: {
			type: 'multi_select_weighted',
			label: localized.multi_select_weighted.label,
			description: localized.multi_select_weighted.description,
			icon: 'fluent:checkbox-person-16-filled',
			requiresAnswer: true,
			manualReview: false
		}
	};
}

export function getStepTemplates(): StepTemplateDefinition[] {
	const localized = getMessages().editor.templateMeta;
	return [
		{
			id: 'trivia',
			label: localized.trivia.label,
			description: localized.trivia.description,
			icon: 'fluent:hat-graduation-16-filled',
			inputKind: 'radio',
			evaluationType: 'exact_text',
			prompt: localized.trivia.prompt,
			options: localized.trivia.options,
			timerSeconds: 30
		},
		{
			id: 'multiple_choice',
			label: localized.multiple_choice.label,
			description: localized.multiple_choice.description,
			icon: 'fluent:checkbox-checked-16-filled',
			inputKind: 'checkbox',
			evaluationType: 'multi_select_weighted',
			prompt: localized.multiple_choice.prompt,
			options: localized.multiple_choice.options,
			timerSeconds: 30
		},
		{
			id: 'closest_guess',
			label: localized.closest_guess.label,
			description: localized.closest_guess.description,
			icon: 'fluent:target-arrow-16-filled',
			inputKind: 'number',
			evaluationType: 'closest_number',
			prompt: localized.closest_guess.prompt,
			placeholder: localized.closest_guess.placeholder,
			timerSeconds: 30
		},
		{
			id: 'exact_number',
			label: localized.exact_number.label,
			description: localized.exact_number.description,
			icon: 'fluent:target-arrow-16-filled',
			inputKind: 'number',
			evaluationType: 'exact_number',
			prompt: localized.exact_number.prompt,
			placeholder: localized.exact_number.placeholder,
			timerSeconds: 30
		},
		{
			id: 'ordering',
			label: localized.ordering.label,
			description: localized.ordering.description,
			icon: 'fluent:re-order-dots-horizontal-16-filled',
			inputKind: 'ordering',
			evaluationType: 'ordering_match',
			prompt: localized.ordering.prompt,
			options: localized.ordering.options,
			timerSeconds: 45
		},
		{
			id: 'open_answer',
			label: localized.open_answer.label,
			description: localized.open_answer.description,
			icon: 'fluent:textbox-16-filled',
			inputKind: 'text',
			evaluationType: 'exact_text',
			prompt: localized.open_answer.prompt,
			placeholder: localized.open_answer.placeholder,
			timerSeconds: 30
		},
		{
			id: 'host_judged',
			label: localized.host_judged.label,
			description: localized.host_judged.description,
			icon: 'fluent:person-feedback-16-filled',
			inputKind: 'text',
			evaluationType: 'host_judged',
			prompt: localized.host_judged.prompt,
			placeholder: localized.host_judged.placeholder,
			timerSeconds: 30
		},
		{
			id: 'buzzer',
			label: localized.buzzer.label,
			description: localized.buzzer.description,
			icon: 'fluent:hand-wave-16-filled',
			inputKind: 'buzzer',
			evaluationType: 'host_judged',
			prompt: localized.buzzer.prompt,
			timerSeconds: 15
		},
		{
			id: 'blank',
			label: localized.blank.label,
			description: localized.blank.description,
			icon: 'fluent:slide-add-16-filled',
			inputKind: 'text',
			evaluationType: 'exact_text',
			prompt: localized.blank.prompt,
			placeholder: localized.blank.placeholder,
			timerSeconds: 30
		}
	];
}

export const MEDIA_TYPES = ['image', 'audio', 'video'] as const;
export const IMAGE_REVEALS = ['none', 'blur_to_clear', 'blur_circle', 'zoom_out'] as const;

function buildRuntimePreviewMedia(media: StepMediaDefinition): RuntimeMediaState {
	const revealState = media.reveal === 'none' ? 'idle' : 'running';
	const sharedState = {
		type_: media.type_,
		src: media.src,
		reveal: media.reveal,
		loop: media.loop,
		reveal_state: revealState,
		reveal_elapsed_seconds: 0,
		reveal_started_at: Date.now() / 1000,
		reveal_duration_seconds: undefined
	};
	if (media.type_ === 'image') {
		return {
			...sharedState,
			type_: 'image',
			zoom_start: media.zoom_start,
			zoom_origin_x: media.zoom_origin_x,
			zoom_origin_y: media.zoom_origin_y
		};
	}
	if (media.type_ === 'audio') {
		return {
			...sharedState,
			type_: 'audio'
		};
	}
	return {
		...sharedState,
		type_: 'video'
	};
}

export function createStepFromTemplate(
	roundIndex: number,
	stepIndex: number,
	templateId: StepTemplateId = 'blank'
): StepDefinition {
	const template =
		getStepTemplates().find((candidate) => candidate.id === templateId) ??
		getStepTemplates().find((candidate) => candidate.id === 'blank');
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
	const evaluations = getEvaluationDetails();
	return INPUT_KIND_EVALUATIONS[kind].map((type) => evaluations[type]);
}

export type StepHealthIssue = {
	id: string;
	label: string;
	icon: string;
};

export function getHostlessEvaluationType(step: StepDefinition): EvaluationType {
	if (step.evaluation.type_ !== 'host_judged') {
		return step.evaluation.type_;
	}
	if (step.player_input.kind === 'text' || step.player_input.kind === 'radio') {
		return 'exact_text';
	}
	if (step.player_input.kind === 'number') {
		return 'exact_number';
	}
	if (step.player_input.kind === 'ordering') {
		return 'ordering_match';
	}
	return 'none';
}

export function isHostlessInformationSlide(step: StepDefinition): boolean {
	return step.player_input.kind === 'none' && step.evaluation.type_ === 'none';
}

export function hasUsableHostlessAnswer(step: StepDefinition): boolean {
	const evaluationType = getHostlessEvaluationType(step);
	if (evaluationType === 'exact_text') {
		return getTextAnswer(step).trim().length > 0;
	}
	if (evaluationType === 'exact_number' || evaluationType === 'closest_number') {
		return Number.isFinite(Number(step.evaluation.answer));
	}
	if (evaluationType === 'ordering_match') {
		return getOrderingAnswer(step).some((value) => value.trim().length > 0);
	}
	if (evaluationType === 'multi_select_weighted') {
		return getCheckboxOptionScores(step).length > 0;
	}
	return false;
}

export function isHostlessCompatibleStep(step: StepDefinition): boolean {
	if (step.player_input.kind === 'buzzer') {
		return false;
	}
	if (isHostlessInformationSlide(step)) {
		return true;
	}
	const evaluationType = getHostlessEvaluationType(step);
	return (
		[
			'exact_text',
			'exact_number',
			'closest_number',
			'ordering_match',
			'multi_select_weighted'
		].includes(evaluationType) && hasUsableHostlessAnswer(step)
	);
}

export function getStepHealthIssues(step: StepDefinition): StepHealthIssue[] {
	const issues: StepHealthIssue[] = [];
	const health = getMessages().editor.health;

	if (!step.title.trim()) {
		issues.push({
			id: 'missing-title',
			label: health.missingTitle,
			icon: 'fluent:textbox-16-filled'
		});
	}

	if (
		['ordering', 'radio', 'checkbox'].includes(step.player_input.kind) &&
		step.player_input.options.filter((option) => option.trim()).length < 2
	) {
		issues.push({
			id: 'missing-options',
			label: health.missingOptions,
			icon: 'fluent:list-16-filled'
		});
	}

	const evaluationDetails = getEvaluationDetails()[step.evaluation.type_];
	const hasAnswer = Array.isArray(step.evaluation.answer)
		? step.evaluation.answer.some((value) => String(value).trim())
		: isCheckboxWeightedAnswer(step.evaluation.answer)
			? step.evaluation.answer.option_scores.length > 0
			: String(step.evaluation.answer ?? '').trim().length > 0;
	if (evaluationDetails.requiresAnswer && !hasAnswer) {
		issues.push({
			id: 'missing-answer',
			label: health.missingAnswer,
			icon: 'fluent:checkmark-circle-warning-16-filled'
		});
	}

	if (step.media && !step.media.src.trim()) {
		issues.push({
			id: 'missing-media',
			label: health.missingMedia,
			icon: 'fluent:image-16-filled'
		});
	}

	if (step.timer.seconds === undefined || step.timer.seconds === null) {
		issues.push({
			id: 'missing-timer',
			label: health.missingTimer,
			icon: 'fluent:timer-off-16-filled'
		});
	}

	if (!isHostlessCompatibleStep(step)) {
		const label =
			step.evaluation.type_ === 'host_judged' && step.player_input.kind === 'checkbox'
				? health.hostlessCheckboxReview
				: step.evaluation.type_ !== 'none' && !hasUsableHostlessAnswer(step)
					? health.hostlessMissingAnswer
					: health.hostlessSkipped;
		issues.push({
			id: 'hostless-incompatible',
			label,
			icon: 'fluent:person-prohibited-16-filled'
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
	return getMessages().editor.previewFallback;
}

export function stepBadges(step: StepDefinition): string[] {
	const badges = [`${step.player_input.kind}`, `${step.evaluation.type_}`];
	if (step.timer.seconds !== undefined) {
		badges.push(formatSeconds(step.timer.seconds));
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

export type CheckboxOptionScore = {
	option: string;
	points: number;
};

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
					...buildRuntimePreviewMedia(step.media),
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
