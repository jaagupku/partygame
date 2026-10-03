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

it('follows game type and run identity from snapshots and patches without accepting stale patches', () => {
	const store = createControllerStore(
		{
			id: 'p1',
			runId: 'r1',
			gameType: 'trivia',
			lastRevision: 1,
			players: []
		} as unknown as ControllerState,
		vi.fn<() => void>()
	);
	const patch = (revision: number, game_type: string, run_id: string) =>
		JSON.stringify({
			type_: 'runtime_patch',
			base_revision: revision,
			revision: revision + 1,
			changes: { lobby: { game_type, run_id } }
		});
	store.onMessage(patch(1, 'price_guessing', 'r2'));
	expect(get(store)).toMatchObject({ gameType: 'price_guessing', runId: 'r2' });
	store.onMessage(patch(2, 'price_guessing', 'r3'));
	expect(get(store).runId).toBe('r3');
	store.onMessage(patch(1, 'drawing_mashup', 'stale'));
	expect(get(store).gameType).toBe('price_guessing');
	store.onMessage(
		JSON.stringify({
			type_: 'runtime_snapshot',
			revision: 4,
			lobby: { game_type: 'calorie_guessing', run_id: 'r4' },
			players: [],
			submitted_player_ids: []
		})
	);
	expect(get(store)).toMatchObject({ gameType: 'calorie_guessing', runId: 'r4' });
});

it('preserves price transition metadata in snapshots and clears it when the opening patch arrives', () => {
	const store = createControllerStore(
		{ id: 'p1', lastRevision: 0 } as ControllerState,
		vi.fn<() => void>()
	);
	const transition = { id: 'run:step2', duration_ms: 600, elapsed_ms: 200 };
	store.onMessage(
		JSON.stringify({
			type_: 'runtime_snapshot',
			revision: 1,
			lobby: { phase: 'price_transition' },
			players: [],
			active_step: { id: 'step2', price_transition: transition, input_enabled: false, timer: {} },
			submitted_player_ids: []
		})
	);
	expect(get(store).activeStep?.price_transition).toEqual(transition);
	expect(get(store).lobbyPhase).toBe('price_transition');
	store.onMessage(
		JSON.stringify({
			type_: 'runtime_patch',
			base_revision: 1,
			revision: 2,
			changes: {
				lobby: { phase: 'question_active' },
				active_step: {
					id: 'step2',
					price_transition: null,
					input_enabled: true,
					timer: { started_at: 100, ends_at: 160 }
				}
			}
		})
	);
	expect(get(store).activeStep?.price_transition).toBeNull();
	expect(get(store).activeStep?.input_enabled).toBe(true);
});
