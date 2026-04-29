import { describe, expect, it } from 'vitest';
import { getMaximumStepPoints, getRadioCorrectOption } from './helpers';

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
});
