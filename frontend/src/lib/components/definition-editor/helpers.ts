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
	usesMap: boolean;
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
	| 'map_point'
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

export const DEFAULT_TIMER_SECONDS = 60;

export const EVALUATION_TYPES: EvaluationType[] = [
	'none',
	'host_judged',
	'exact_text',
	'exact_number',
	'closest_number',
	'ordering_match',
	'multi_select_weighted',
	'map_distance',
	'favorite_vote'
];

export const INPUT_KIND_EVALUATIONS: Record<PlayerInputKind, EvaluationType[]> = {
	none: ['none'],
	buzzer: ['host_judged'],
	text: ['none', 'host_judged', 'exact_text'],
	number: ['none', 'host_judged', 'exact_number', 'closest_number'],
	ordering: ['none', 'host_judged', 'ordering_match'],
	radio: ['none', 'host_judged', 'exact_text'],
	checkbox: ['none', 'host_judged', 'multi_select_weighted'],
	map: ['none', 'host_judged', 'map_distance'],
	drawing: ['none', 'favorite_vote']
};

export const DEFAULT_EVALUATION_BY_INPUT_KIND: Record<PlayerInputKind, EvaluationType> = {
	none: 'none',
	buzzer: 'host_judged',
	text: 'exact_text',
	number: 'exact_number',
	ordering: 'ordering_match',
	radio: 'exact_text',
	checkbox: 'multi_select_weighted',
	map: 'map_distance',
	drawing: 'favorite_vote'
};

export const DEFAULT_MAP_CONFIG: MapInputConfig = {
	selection_mode: 'point',
	base_layer: 'osm',
	bounds: {
		north: 85,
		south: -85,
		east: 180,
		west: -180
	},
	initial_center: {
		lat: 20,
		lng: 0
	},
	initial_zoom: 2,
	min_zoom: 2,
	max_zoom: 18
};

export function buildDefaultMapDistanceAnswer(
	mapConfig: MapInputConfig = DEFAULT_MAP_CONFIG
): MapDistanceAnswer {
	return {
		correct_point: { ...mapConfig.initial_center },
		scoring_mode: 'bands',
		max_points: 5,
		zero_distance_m: null,
		full_credit_distance_m: null,
		bands: [
			{ distance_m: 500, points: 5, label: 'Exact area' },
			{ distance_m: 5_000, points: 3, label: 'Nearby' },
			{ distance_m: 20_000, points: 1, label: 'Same region' }
		]
	};
}

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
			usesNumericRange: false,
			usesMap: false
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
			usesNumericRange: true,
			usesMap: false
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
			usesNumericRange: false,
			usesMap: false
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
			usesNumericRange: false,
			usesMap: false
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
			usesNumericRange: false,
			usesMap: false
		},
		map: {
			kind: 'map',
			label: localized.map.label,
			description: localized.map.description,
			icon: 'fluent:map-16-filled',
			recommendedEvaluation: 'map_distance',
			usesPrompt: true,
			usesPlaceholder: false,
			usesOptions: false,
			usesNumericRange: false,
			usesMap: true
		},
		drawing: {
			kind: 'drawing',
			label: localized.drawing.label,
			description: localized.drawing.description,
			icon: 'fluent:draw-shape-24-filled',
			recommendedEvaluation: 'favorite_vote',
			usesPrompt: true,
			usesPlaceholder: false,
			usesOptions: false,
			usesNumericRange: false,
			usesMap: false
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
			usesNumericRange: false,
			usesMap: false
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
			usesNumericRange: false,
			usesMap: false
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
		},
		map_distance: {
			type: 'map_distance',
			label: localized.map_distance.label,
			description: localized.map_distance.description,
			icon: 'fluent:map-16-filled',
			requiresAnswer: true,
			manualReview: false
		},
		favorite_vote: {
			type: 'favorite_vote',
			label: localized.favorite_vote.label,
			description: localized.favorite_vote.description,
			icon: 'fluent:heart-16-filled',
			requiresAnswer: false,
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
			timerSeconds: DEFAULT_TIMER_SECONDS
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
			timerSeconds: DEFAULT_TIMER_SECONDS
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
			timerSeconds: DEFAULT_TIMER_SECONDS
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
			timerSeconds: DEFAULT_TIMER_SECONDS
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
			timerSeconds: DEFAULT_TIMER_SECONDS
		},
		{
			id: 'map_point',
			label: localized.map_point.label,
			description: localized.map_point.description,
			icon: 'fluent:map-16-filled',
			inputKind: 'map',
			evaluationType: 'map_distance',
			prompt: localized.map_point.prompt,
			timerSeconds: DEFAULT_TIMER_SECONDS
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
			timerSeconds: DEFAULT_TIMER_SECONDS
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
			timerSeconds: DEFAULT_TIMER_SECONDS
		},
		{
			id: 'buzzer',
			label: localized.buzzer.label,
			description: localized.buzzer.description,
			icon: 'fluent:hand-wave-16-filled',
			inputKind: 'buzzer',
			evaluationType: 'host_judged',
			prompt: localized.buzzer.prompt,
			timerSeconds: DEFAULT_TIMER_SECONDS
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
			timerSeconds: DEFAULT_TIMER_SECONDS
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
		paused: media.type_ === 'video' ? !(media.autoplay ?? true) : false,
		reveal: media.reveal,
		loop: media.loop,
		autoplay: media.type_ === 'video' ? (media.autoplay ?? true) : true,
		hide_youtube_title: media.type_ === 'video' ? (media.hide_youtube_title ?? false) : false,
		playback_revision: 0,
		reveal_state: revealState,
		reveal_elapsed_seconds: 0,
		reveal_started_at: Date.now() / 1000,
		reveal_duration_seconds: undefined
	};
	if (media.type_ === 'image') {
		return {
			...sharedState,
			type_: 'image',
			blur_amount: media.blur_amount,
			blur_circle_start_size: media.blur_circle_start_size,
			blur_circle_background: media.blur_circle_background,
			blur_circle_background_color: media.blur_circle_background_color,
			blur_reveal_curve: media.blur_reveal_curve,
			blur_circle_reveal_curve: media.blur_circle_reveal_curve,
			zoom_reveal_curve: media.zoom_reveal_curve,
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
	} else if (template?.evaluationType === 'exact_text') {
		answer = template?.inputKind === 'radio' ? (options[0] ?? '') : [''];
	} else if (
		template?.evaluationType === 'exact_number' ||
		template?.evaluationType === 'closest_number'
	) {
		answer = 0;
	} else if (template?.evaluationType === 'map_distance') {
		answer = buildDefaultMapDistanceAnswer();
	} else if (template?.evaluationType === 'none') {
		answer = null;
	}

	return {
		id: `step_${roundIndex}_${stepIndex}`,
		title: `Step ${stepIndex}`,
		body: '',
		timer: {
			seconds: template?.timerSeconds ?? DEFAULT_TIMER_SECONDS,
			enforced: false
		},
		player_input: {
			kind: template?.inputKind ?? 'text',
			prompt: template?.prompt ?? '',
			placeholder: template?.placeholder ?? '',
			options,
			min_value: undefined,
			max_value: undefined,
			step: undefined,
			map: template?.inputKind === 'map' ? structuredClone(DEFAULT_MAP_CONFIG) : undefined
		},
		evaluation: {
			type_: template?.evaluationType ?? 'exact_text',
			points: 1,
			answer,
			max_distance: template?.evaluationType === 'exact_text' ? 2 : undefined,
			number_bands: template?.evaluationType === 'closest_number' ? [] : undefined
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
	if (step.player_input.kind === 'map') {
		return 'map_distance';
	}
	return 'none';
}

export function isHostlessInformationSlide(step: StepDefinition): boolean {
	return step.player_input.kind === 'none' && step.evaluation.type_ === 'none';
}

export function hasUsableHostlessAnswer(step: StepDefinition): boolean {
	const evaluationType = getHostlessEvaluationType(step);
	if (evaluationType === 'exact_text') {
		return getTextAnswers(step).some((value) => value.trim().length > 0);
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
	if (evaluationType === 'map_distance') {
		return getMapDistanceAnswer(step) !== null;
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
			'multi_select_weighted',
			'map_distance'
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
			: isMapDistanceAnswer(step.evaluation.answer)
				? Boolean(step.evaluation.answer.correct_point)
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
	const availableOptions = [...step.player_input.options];
	const unusedOptions = [...availableOptions];
	const answer = Array.isArray(step.evaluation.answer)
		? step.evaluation.answer.map((value) => String(value))
		: availableOptions;
	const orderedOptions: string[] = [];
	for (const value of answer) {
		const optionIndex = unusedOptions.indexOf(value);
		if (optionIndex === -1) {
			continue;
		}
		orderedOptions.push(unusedOptions.splice(optionIndex, 1)[0]);
	}
	return [...orderedOptions, ...unusedOptions];
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

export function isMapPoint(value: unknown): value is MapPoint {
	if (!value || typeof value !== 'object') {
		return false;
	}
	const point = value as Partial<MapPoint>;
	return Number.isFinite(Number(point.lat)) && Number.isFinite(Number(point.lng));
}

export function isMapDistanceAnswer(answer: unknown): answer is MapDistanceAnswer {
	if (!answer || typeof answer !== 'object' || !('correct_point' in answer)) {
		return false;
	}
	const value = answer as Partial<MapDistanceAnswer>;
	return isMapPoint(value.correct_point);
}

export function normalizeMapDistanceAnswerForMode(
	answer: MapDistanceAnswer,
	mapConfig: MapInputConfig = DEFAULT_MAP_CONFIG
): MapDistanceAnswer {
	const defaults = buildDefaultMapDistanceAnswer(mapConfig);
	const scoringMode = answer.scoring_mode ?? defaults.scoring_mode;
	const normalized: MapDistanceAnswer = {
		...defaults,
		...answer,
		scoring_mode: scoringMode,
		correct_point: {
			lat: Number(answer.correct_point.lat),
			lng: Number(answer.correct_point.lng)
		},
		bands: Array.isArray(answer.bands) ? answer.bands : []
	};

	if (scoringMode === 'bands') {
		return {
			...normalized,
			zero_distance_m: null,
			full_credit_distance_m: null
		};
	}

	return {
		...normalized,
		zero_distance_m: Math.max(1, Number(answer.zero_distance_m ?? 50_000) || 1),
		full_credit_distance_m: Math.max(0, Number(answer.full_credit_distance_m ?? 500) || 0)
	};
}

export function getMapDistanceAnswer(step: StepDefinition): MapDistanceAnswer | null {
	if (isMapDistanceAnswer(step.evaluation.answer)) {
		return normalizeMapDistanceAnswerForMode(
			step.evaluation.answer,
			step.player_input.map ?? DEFAULT_MAP_CONFIG
		);
	}
	if (step.player_input.kind === 'map' && step.evaluation.type_ === 'map_distance') {
		return buildDefaultMapDistanceAnswer(step.player_input.map ?? DEFAULT_MAP_CONFIG);
	}
	return null;
}

export function clampMapPointToBounds(point: MapPoint, bounds: MapBounds): MapPoint {
	return {
		lat: Math.min(bounds.north, Math.max(bounds.south, point.lat)),
		lng: Math.min(bounds.east, Math.max(bounds.west, point.lng))
	};
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

export function getRadioCorrectOption(step: StepDefinition): string {
	if (step.player_input.kind !== 'radio' || step.evaluation.type_ !== 'exact_text') {
		return '';
	}
	if (Array.isArray(step.evaluation.answer) || isCheckboxWeightedAnswer(step.evaluation.answer)) {
		return '';
	}
	const answer = String(step.evaluation.answer ?? '');
	return (
		step.player_input.options.find((option) => option === answer) ??
		step.player_input.options.find((option) => option.trim() === answer.trim()) ??
		''
	);
}

export function getTextAnswer(step: StepDefinition): string {
	if (
		Array.isArray(step.evaluation.answer) ||
		isCheckboxWeightedAnswer(step.evaluation.answer) ||
		isMapDistanceAnswer(step.evaluation.answer)
	) {
		return '';
	}
	return String(step.evaluation.answer ?? '');
}

export function getTextAnswers(step: StepDefinition): string[] {
	if (Array.isArray(step.evaluation.answer)) {
		return step.evaluation.answer.map((value) => String(value));
	}
	if (isCheckboxWeightedAnswer(step.evaluation.answer)) {
		return [];
	}
	if (isMapDistanceAnswer(step.evaluation.answer)) {
		return [''];
	}
	const value = String(step.evaluation.answer ?? '');
	return value ? [value] : [''];
}

export function getExactTextMaxDistance(step: StepDefinition): number {
	const value = Number(step.evaluation.max_distance ?? 2);
	return Number.isFinite(value) ? Math.max(0, Math.trunc(value)) : 2;
}

export function getNumberAnswer(step: StepDefinition): number | undefined {
	const value = Number(step.evaluation.answer);
	return Number.isFinite(value) ? value : undefined;
}

export function getNumberToleranceBands(step: StepDefinition): NumberToleranceBand[] {
	return (step.evaluation.number_bands ?? []).map((band) => ({
		distance: Number.isFinite(Number(band.distance)) ? Math.max(0, Number(band.distance)) : 0,
		points: Number.isFinite(Number(band.points)) ? Math.max(0, Math.trunc(Number(band.points))) : 0,
		label: band.label ?? ''
	}));
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
	if (step.evaluation.type_ === 'map_distance') {
		const answer = getMapDistanceAnswer(step);
		if (!answer) {
			return null;
		}
		return normalizeMapDistanceAnswerForMode(answer, step.player_input.map ?? DEFAULT_MAP_CONFIG);
	}
	if (step.evaluation.type_ === 'exact_text' && step.player_input.kind === 'text') {
		const values = getTextAnswers(step)
			.map((value) => value.trim())
			.filter(Boolean);
		return values.length > 0 ? values : null;
	}
	const value = getTextAnswer(step).trim();
	return value || null;
}

export function getMaximumStepPoints(step: StepDefinition): number {
	if (step.evaluation.type_ === 'closest_number') {
		return Math.max(
			step.evaluation.points,
			...getNumberToleranceBands(step).map((band) => band.points)
		);
	}
	if (step.evaluation.type_ === 'map_distance') {
		return getMapDistanceAnswer(step)?.max_points ?? step.evaluation.points;
	}
	if (step.evaluation.type_ !== 'multi_select_weighted') {
		return step.evaluation.points;
	}
	return getCheckboxOptionScores(step).reduce(
		(total, entry) => total + Math.max(0, Math.trunc(entry.points)),
		0
	);
}

export function buildRuntimePreviewStep(step: StepDefinition): RuntimeStepState {
	return {
		id: step.id,
		title: step.title,
		body: step.body,
		evaluation_type: step.evaluation.type_,
		evaluation_points: step.evaluation.points,
		evaluation_answer: step.evaluation.answer,
		max_points: getMaximumStepPoints(step),
		input_enabled: true,
		input_kind: step.player_input.kind,
		input_prompt: step.player_input.prompt,
		input_placeholder: step.player_input.placeholder,
		input_options: [...step.player_input.options],
		slider_min: step.player_input.min_value,
		slider_max: step.player_input.max_value,
		slider_step: step.player_input.step,
		map: step.player_input.map,
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
