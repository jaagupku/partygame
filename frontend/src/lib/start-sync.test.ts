import { get } from 'svelte/store';
import { expect, it, vi } from 'vitest';
import { createControllerStore } from './controller-store';
import { createGameStore } from './game-store';

it('requests authoritative state on start notification on display and controller', () => {
	const display = createGameStore({
		players: [],
		state: 'waiting_for_players'
	} as unknown as Lobby);
	const phone = createControllerStore(
		{ gameState: 'waiting_for_players' } as ControllerState,
		vi.fn<() => void>()
	);
	for (const store of [display, phone]) {
		expect(store.onMessage(JSON.stringify({ type_: 'start_game' }))).toBe('resync_required');
	}
	// A notification alone must not open answering before the server snapshot arrives.
	expect(get(display).state).toBe('waiting_for_players');
	expect(get(phone).gameState).toBe('waiting_for_players');
});
