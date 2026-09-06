import { get } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import { createControllerStore } from './controller-store';

describe('controller question resets', () => {
	it.each(['runtime_snapshot', 'runtime_patch'])(
		'clears stale rejection state on a same-question reset via %s',
		(type_) => {
			const oldStep = { id: 'question', input_enabled: true, timer: { started_at: 100 } };
			const newStep = { ...oldStep, timer: { started_at: 200 } };
			const store = createControllerStore(
				{
					id: 'p1',
					activeStep: oldStep,
					lastRevision: 1,
					displayPhase: 'question_active',
					answerResult: 'wrong',
					submissionError: 'step_closed',
					hasSubmitted: false
				} as ControllerState,
				vi.fn<() => void>()
			);
			const event =
				type_ === 'runtime_snapshot'
					? {
							type_,
							revision: 2,
							lobby: { phase: 'question_active' },
							players: [],
							active_step: newStep,
							display_phase: 'question_active',
							submitted_player_ids: []
						}
					: {
							type_,
							base_revision: 1,
							revision: 2,
							changes: { active_step: newStep, submitted_player_ids: [] }
						};
			store.onMessage(JSON.stringify(event));
			expect(get(store).submissionError).toBeUndefined();
			expect(get(store).answerResult).toBe('none');
			expect(get(store).hasSubmitted).toBe(false);
		}
	);
});
