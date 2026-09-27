import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { createGameStore } from './game-store';
import { waitingPlayers } from './waiting-players';

function state(): HostGameState {
	return {
		...get(
			createGameStore({
				id: 'lobby',
				run_id: 'run',
				host_id: 'host',
				host_enabled: true,
				state: 'running',
				phase: 'question_active',
				current_step: 1,
				players: ['host', 'a', 'b', 'c'].map((id) => ({ id, name: id, status: 'connected' }))
			} as Lobby)
		),
		activeStep: {
			id: 'drawing',
			input_kind: 'drawing',
			input_enabled: true,
			evaluation_type: 'favorite_vote',
			timer: { started_at: 100 }
		} as RuntimeStepState
	};
}
const ids = (s: HostGameState) => waitingPlayers(s).players.map((p) => p.id);

describe('waiting players', () => {
	it.each(['drawing', 'text', 'number', 'radio', 'checkbox', 'ordering', 'map'])(
		'tracks accepted %s answers',
		(kind) => {
			const s = state();
			s.activeStep!.input_kind = kind as PlayerInputKind;
			s.submittedPlayerIds = ['a'];
			expect(ids(s)).toEqual(['b', 'c']);
		}
	);
	it('tracks only required drawing voters', () => {
		const s = state();
		s.displayPhase = 'drawing_vote';
		s.submittedPlayerIds = ['a', 'b'];
		s.drawingVotedPlayerIds = ['a'];
		expect(waitingPlayers(s).action).toBe('vote');
		expect(ids(s)).toEqual(['b']);
	});
	it('removes disconnected and kicked players and restores only unfinished reconnects', () => {
		const s = state();
		s.players[1].status = 'disconnected';
		expect(ids(s)).toEqual(['b', 'c']);
		s.players[1].status = 'connected';
		expect(ids(s)).toEqual(['a', 'b', 'c']);
		s.submittedPlayerIds = ['a'];
		s.players = s.players.filter((p) => p.id !== 'b');
		expect(ids(s)).toEqual(['c']);
	});
	it('tracks eligible buzzers only while open, including reopening', () => {
		const s = state();
		s.activeStep!.input_kind = 'buzzer';
		s.buzzerActive = true;
		s.disabledBuzzerPlayerIds = ['a'];
		expect(ids(s)).toEqual(['b', 'c']);
		s.buzzerActive = false;
		expect(ids(s)).toEqual([]);
		s.buzzerActive = true;
		expect(ids(s)).toEqual(['b', 'c']);
	});
	it('tracks ready toggles during hostless price reveals', () => {
		const s = state();
		s.host_enabled = false;
		s.host_id = undefined;
		s.phase = 'step_complete';
		s.displayPhase = 'answer_reveal';
		s.activeStep!.price_mode = 'guess';
		s.priceRevealRemainingSeconds = 5;
		s.priceReadyPlayerIds = ['a'];
		expect(ids(s)).toEqual(['host', 'b', 'c']);
		s.priceReadyPlayerIds = [];
		expect(ids(s)).toContain('a');
		s.priceRevealRemainingSeconds = 0;
		expect(ids(s)).toEqual([]);
	});
	it('waits only for the hostless starter on info slides', () => {
		const s = state();
		s.host_enabled = false;
		s.starter_id = 'b';
		s.activeStep!.input_kind = 'none';
		s.activeStep!.evaluation_type = 'none';
		expect(ids(s)).toEqual(['b']);
		s.host_enabled = true;
		expect(ids(s)).toEqual([]);
	});
	it('hides inactive, historical, intro and finished phases', () => {
		for (const overrides of [
			{ reviewingHistory: true },
			{ phase: 'finished' },
			{ state: 'paused' },
			{ displayPhase: 'answer_reveal' },
			{ activeItem: { type_: 'round_intro' } },
			{ activeStep: undefined },
			{ endGame: { revealed: true } }
		])
			expect(ids({ ...state(), ...overrides } as HostGameState)).toEqual([]);
	});
	it('keeps identity through updates and resets for run, step, restart and phase', () => {
		const s = state();
		const key = waitingPlayers(s).key;
		s.submittedPlayerIds = ['a'];
		expect(waitingPlayers(s).key).toBe(key);
		for (const changed of [
			{ ...s, run_id: 'new' },
			{ ...s, current_step: 2 },
			{ ...s, displayPhase: 'drawing_vote' },
			{ ...s, activeStep: { ...s.activeStep!, timer: { ...s.activeStep!.timer, started_at: 200 } } }
		])
			expect(waitingPlayers(changed).key).not.toBe(key);
	});
});

it('synchronizes completion lists through patches and resync snapshots', () => {
	const store = createGameStore(state());
	const snapshot = {
		type_: 'runtime_snapshot',
		revision: 1,
		lobby: state(),
		players: state().players,
		submitted_player_ids: ['a'],
		price_ready_player_ids: ['b'],
		price_reveal_remaining_seconds: 5,
		drawing_voted_player_ids: ['c']
	};
	store.onMessage(JSON.stringify(snapshot));
	expect(get(store)).toMatchObject({
		submittedPlayerIds: ['a'],
		priceReadyPlayerIds: ['b'],
		drawingVotedPlayerIds: ['c'],
		priceRevealRemainingSeconds: 5
	});
	const patch = {
		type_: 'runtime_patch',
		base_revision: 1,
		revision: 2,
		changes: {
			submitted_player_ids: [],
			price_ready_player_ids: [],
			drawing_voted_player_ids: [],
			price_reveal_remaining_seconds: null
		}
	};
	store.onMessage(JSON.stringify(patch));
	expect(get(store)).toMatchObject({
		submittedPlayerIds: [],
		priceReadyPlayerIds: [],
		drawingVotedPlayerIds: [],
		priceRevealRemainingSeconds: undefined
	});
	expect(store.onMessage(JSON.stringify({ ...patch, base_revision: 0 }))).toBe('resync_required');
	store.onMessage(JSON.stringify({ ...snapshot, revision: 3 }));
	expect(get(store).submittedPlayerIds).toEqual(['a']);
	store.onMessage(JSON.stringify({ ...snapshot, revision: 2, submitted_player_ids: ['b'] }));
	expect(get(store).submittedPlayerIds).toEqual(['a']);
});
