import { describe, expect, it } from 'vitest';
import {
	DEFAULT_TIMER_SECONDS,
	buildRuntimePreviewStep,
	createStepFromTemplate,
	getExactTextMaxDistance,
	getMapDistanceAnswer,
	getMaximumStepPoints,
	getRadioCorrectOption,
	normalizeAnswer,
	normalizeMapDistanceAnswerForMode
} from './helpers';

describe('definition editor helpers', () => {
	it('matches saved radio answers to the canonical option text', () => {
		const step = {
			id: 'step_1',
			title: 'Trivia',
			body: '',
			timer: { seconds: 30, enforced: false },
			player_input: {
				kind: 'radio',
				options: ['Sentinel 2', 'Landsat 8', 'Euclid'],
				prompt: '',
				placeholder: ''
			},
			evaluation: {
				type_: 'exact_text',
				points: 1,
				answer: ' Sentinel 2 '
			},
			host_behavior: {
				reveal_answers: true,
				show_submissions: true,
				allow_custom_points: true
			}
		} satisfies StepDefinition;

		expect(getRadioCorrectOption(step)).toBe('Sentinel 2');
	});

	it('normalizes exact text aliases by trimming blanks', () => {
		const step = {
			id: 'step_1',
			title: 'Trivia',
			body: '',
			timer: { seconds: 30, enforced: false },
			player_input: {
				kind: 'text',
				options: [],
				prompt: '',
				placeholder: ''
			},
			evaluation: {
				type_: 'exact_text',
				points: 1,
				answer: [' Paris ', '', ' City of Light '],
				max_distance: 2
			},
			host_behavior: {
				reveal_answers: true,
				show_submissions: true,
				allow_custom_points: true
			}
		} satisfies StepDefinition;

		expect(normalizeAnswer(step)).toEqual(['Paris', 'City of Light']);
	});

	it('defaults new exact text steps to typo distance 2', () => {
		const step = createStepFromTemplate(0, 0, 'open_answer');

		expect(step.evaluation.type_).toBe('exact_text');
		expect(getExactTextMaxDistance(step)).toBe(2);
		expect(step.timer.seconds).toBe(DEFAULT_TIMER_SECONDS);
	});

	it('calculates checkbox weighted maximum from positive option scores', () => {
		const step = {
			id: 'step_1',
			title: 'Weighted',
			body: '',
			timer: { seconds: 30, enforced: false },
			player_input: {
				kind: 'checkbox',
				options: ['Mercury', 'Venus', 'Pluto'],
				prompt: '',
				placeholder: ''
			},
			evaluation: {
				type_: 'multi_select_weighted',
				points: 1,
				answer: {
					option_scores: [
						{ option: 'Mercury', points: 2 },
						{ option: 'Venus', points: 3 },
						{ option: 'Pluto', points: -1 }
					]
				}
			},
			host_behavior: {
				reveal_answers: true,
				show_submissions: true,
				allow_custom_points: true
			}
		} satisfies StepDefinition;

		expect(getMaximumStepPoints(step)).toBe(5);
	});

	it('preserves image reveal curves in runtime previews', () => {
		const step = {
			id: 'step_1',
			title: 'Image',
			body: '',
			timer: { seconds: 30, enforced: false },
			player_input: {
				kind: 'none',
				options: [],
				prompt: '',
				placeholder: ''
			},
			evaluation: {
				type_: 'none',
				points: 0,
				answer: undefined
			},
			host_behavior: {
				reveal_answers: true,
				show_submissions: true,
				allow_custom_points: true
			},
			media: {
				type_: 'image',
				src: '/image.png',
				reveal: 'zoom_out',
				loop: false,
				blur_reveal_curve: [0.1, 0.2, 0.3, 0.4],
				blur_circle_reveal_curve: [0.2, 0.3, 0.4, 0.5],
				zoom_reveal_curve: [0.3, 0.4, 0.5, 0.6]
			}
		} satisfies StepDefinition;

		const preview = buildRuntimePreviewStep(step);

		expect(preview.media?.type_).toBe('image');
		if (preview.media?.type_ !== 'image') {
			throw new Error('Expected image media');
		}
		expect(preview.media.blur_reveal_curve).toEqual([0.1, 0.2, 0.3, 0.4]);
		expect(preview.media.blur_circle_reveal_curve).toEqual([0.2, 0.3, 0.4, 0.5]);
		expect(preview.media.zoom_reveal_curve).toEqual([0.3, 0.4, 0.5, 0.6]);
	});

	it('creates map steps with runtime map config and map max points', () => {
		const step = createStepFromTemplate(0, 0, 'map_point');

		expect(step.player_input.kind).toBe('map');
		expect(step.evaluation.type_).toBe('map_distance');
		expect(getMapDistanceAnswer(step)?.max_points).toBe(5);
		expect(getMaximumStepPoints(step)).toBe(5);

		const preview = buildRuntimePreviewStep(step);

		expect(preview.input_kind).toBe('map');
		expect(preview.map?.selection_mode).toBe('point');
		expect(preview.max_points).toBe(5);
	});

	it('normalizes map distance answers for saving', () => {
		const step = createStepFromTemplate(0, 0, 'map_point');
		step.evaluation.answer = {
			correct_point: { lat: 59.4, lng: 24.7 },
			scoring_mode: 'linear',
			max_points: 7,
			zero_distance_m: 10000,
			full_credit_distance_m: 1000,
			bands: []
		};

		expect(normalizeAnswer(step)).toEqual(step.evaluation.answer);
		expect(getMaximumStepPoints(step)).toBe(7);
	});

	it('normalizes map band scoring without smooth decay distances', () => {
		const answer = normalizeMapDistanceAnswerForMode({
			correct_point: { lat: 59.4, lng: 24.7 },
			scoring_mode: 'bands',
			max_points: 5,
			zero_distance_m: 10000,
			full_credit_distance_m: 1000,
			bands: [{ distance_m: 500, points: 5, label: 'Close' }]
		});

		expect(answer.zero_distance_m).toBeNull();
		expect(answer.full_credit_distance_m).toBeNull();
		expect(answer.bands).toEqual([{ distance_m: 500, points: 5, label: 'Close' }]);
	});

	it('normalizes map smooth decay scoring with required distances', () => {
		const answer = normalizeMapDistanceAnswerForMode({
			correct_point: { lat: 59.4, lng: 24.7 },
			scoring_mode: 'linear',
			max_points: 5,
			zero_distance_m: null,
			full_credit_distance_m: null,
			bands: [{ distance_m: 500, points: 5, label: 'Close' }]
		});

		expect(answer.zero_distance_m).toBe(50000);
		expect(answer.full_credit_distance_m).toBe(500);
	});
});
