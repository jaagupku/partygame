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

it('resets finale and answer feedback on a new run and ignores an older snapshot', () => {
	const store = createControllerStore(
		{
			id: 'p1',
			runId: 'old',
			lastRevision: 8,
			isHost: true,
			answerResult: 'correct',
			submissionError: 'step_closed',
			endGame: { revealed: true },
			lastReaction: { reaction: '🔥' }
		} as unknown as ControllerState,
		vi.fn<() => void>()
	);
	const snapshot = {
		type_: 'runtime_snapshot',
		revision: 9,
		lobby: {
			run_id: 'new',
			host_enabled: false,
			host_id: null,
			starter_id: 'p1',
			state: 'waiting_for_players',
			phase: 'waiting',
			current_step: 0
		},
		players: [{ id: 'p1', score: 0 }],
		submitted_player_ids: [],
		active_step: null,
		end_game: null,
		submissions: [],
		display_phase: 'question_active'
	};
	store.onMessage(JSON.stringify(snapshot));
	expect(get(store)).toMatchObject({
		runId: 'new',
		gameState: 'waiting_for_players',
		isHost: false,
		answerResult: 'none',
		hasSubmitted: false,
		endGame: null
	});
	expect(get(store).submissionError).toBeUndefined();
	expect(get(store).lastReaction).toBeUndefined();
	store.onMessage(
		JSON.stringify({ ...snapshot, revision: 8, lobby: { run_id: 'old', phase: 'finished' } })
	);
	expect(get(store).runId).toBe('new');
	expect(get(store).lobbyPhase).toBe('waiting');
});
