import { describe, expect, it } from 'vitest';
import { buildRuntimePreviewStep, getMaximumStepPoints, getRadioCorrectOption } from './helpers';

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
});
