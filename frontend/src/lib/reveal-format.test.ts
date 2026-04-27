import { describe, expect, it } from 'vitest';

import { buildOrderingRevealItems, buildRevealedOptionStates } from '$lib/reveal-format.js';

function optionStep(overrides: Partial<RuntimeStepState> = {}): RuntimeStepState {
	return {
		id: 'step-1',
		title: 'Question',
		evaluation_type: 'exact_text',
		evaluation_points: 3,
		input_enabled: true,
		input_kind: 'radio',
		input_options: ['A', 'B', 'C'],
		timer: {
			seconds: 10,
			enforced: false,
			started_at: undefined,
			ends_at: undefined,
			remaining_seconds: 10
		},
		...overrides
	};
}

describe('revealed option states', () => {
	it('marks the radio correct option green with question points', () => {
		const states = buildRevealedOptionStates(optionStep(), { value: 'B' });

		expect(states).toEqual([
			{ option: 'A', correct: false, points: 0, pointsLabel: '0 pts' },
			{ option: 'B', correct: true, points: 3, pointsLabel: '+3 pts' },
			{ option: 'C', correct: false, points: 0, pointsLabel: '0 pts' }
		]);
	});

	it('maps checkbox weighted points to green positive and red non-positive states', () => {
		const states = buildRevealedOptionStates(
			optionStep({
				evaluation_type: 'multi_select_weighted',
				input_kind: 'checkbox',
				input_options: ['Mercury', 'Venus', 'Mars']
			}),
			{
				value: {
					option_scores: [
						{ option: 'Mercury', points: 2 },
						{ option: 'Venus', points: 0 },
						{ option: 'Mars', points: -1 }
					]
				}
			}
		);

		expect(states).toEqual([
			{ option: 'Mercury', correct: true, points: 2, pointsLabel: '+2 pts' },
			{ option: 'Venus', correct: false, points: 0, pointsLabel: '0 pts' },
			{ option: 'Mars', correct: false, points: -1, pointsLabel: '-1 pts' }
		]);
	});

	it('falls back missing checkbox weighted scores to red zero-point states', () => {
		const states = buildRevealedOptionStates(
			optionStep({
				evaluation_type: 'multi_select_weighted',
				input_kind: 'checkbox',
				input_options: ['A', 'B']
			}),
			{
				value: {
					option_scores: [{ option: 'A', points: 1 }]
				}
			}
		);

		expect(states).toEqual([
			{ option: 'A', correct: true, points: 1, pointsLabel: '+1 pts' },
			{ option: 'B', correct: false, points: 0, pointsLabel: '0 pts' }
		]);
	});

	it('returns no states for non-option reveal steps', () => {
		const states = buildRevealedOptionStates(
			optionStep({
				evaluation_type: 'exact_text',
				input_kind: 'text',
				input_options: []
			}),
			{ value: 'Answer' }
		);

		expect(states).toEqual([]);
	});
});

describe('ordering reveal items', () => {
	it('uses input option order before reveal', () => {
		const items = buildOrderingRevealItems(
			optionStep({
				evaluation_type: 'ordering_match',
				input_kind: 'ordering',
				input_options: ['3', '1', '2']
			}),
			{ value: ['1', '2', '3'] },
			false
		);

		expect(items).toEqual(['3', '1', '2']);
	});

	it('reorders to the revealed correct order and appends missing options', () => {
		const items = buildOrderingRevealItems(
			optionStep({
				evaluation_type: 'ordering_match',
				input_kind: 'ordering',
				input_options: ['3', '1', '2', '4']
			}),
			{ value: ['1', '2', '3'] },
			true
		);

		expect(items).toEqual(['1', '2', '3', '4']);
	});
});
