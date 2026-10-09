import { afterEach, expect, it, vi } from 'vitest';
import { createPresentationSystem } from './system';
import { registerPresentation } from './registry';
const { play, activate, dispose, legacySync, legacyEvent } = vi.hoisted(() => ({
	play: vi.fn(),
	activate: vi.fn(async () => true),
	dispose: vi.fn(),
	legacySync: vi.fn(),
	legacyEvent: vi.fn()
}));
vi.mock('./audio-driver', () => ({
	createBrowserAudioDriver: () => ({ activate, play, dispose })
}));
vi.mock('$lib/sound-system', () => ({
	createSoundSystem: () => ({
		syncState: legacySync,
		handleEvent: legacyEvent,
		start: vi.fn(),
		tick: vi.fn(),
		dispose: vi.fn()
	})
}));
const cleanups: (() => void)[] = [];
afterEach(() => {
	cleanups.reverse().forEach((fn) => fn());
	cleanups.length = 0;
	vi.clearAllMocks();
	vi.useRealTimers();
});
function setup(surface: 'controller' | 'host-display') {
	play.mockImplementation(() => ({ volume: vi.fn(), stop: vi.fn() }));
	cleanups.push(
		registerPresentation(
			{
				gameType: 'drawing_mashup',
				appearance: { palette: {} },
				audio: {
					music: 'music',
					effects: {
						buzz: { src: 'buzz' },
						submissionReceived: { src: 'accepted' },
						answerReveal: { src: 'reveal' },
						timerWarning: { src: 'tick' }
					}
				}
			},
			{ replace: true }
		)
	);
	const system = createPresentationSystem(surface);
	cleanups.push(system.dispose);
	system.setConnected(true);
	return system;
}
function state(overrides = {}): ControllerState {
	return {
		id: 'self',
		gameType: 'drawing_mashup',
		runId: 'one',
		gameState: 'running',
		hasSubmitted: false,
		submissionCount: 0,
		activeStep: { id: 'step', input_kind: 'number', input_enabled: true, timer: {} },
		...overrides
	} as ControllerState;
}
it('only confirms the current player, not aggregate submissions or drawing saves', async () => {
	const system = setup('controller');
	system.syncState(state());
	await Promise.resolve();
	system.syncState(state({ submissionCount: 1 }));
	expect(play).not.toHaveBeenCalled();
	system.syncState(state({ submissionCount: 2, hasSubmitted: true }));
	expect(play).toHaveBeenCalledTimes(1);
	expect(play.mock.calls[0][0]).toBe('accepted');
	system.syncState(state({ submissionCount: 3, hasSubmitted: true }));
	expect(play).toHaveBeenCalledTimes(1);
	system.syncState(state({ runId: 'two', hasSubmitted: true }));
	expect(play).toHaveBeenCalledTimes(1);
	system.syncState(
		state({
			runId: 'two',
			activeStep: { id: 'draw', input_kind: 'drawing', timer: {} },
			hasSubmitted: true
		})
	);
	expect(play).toHaveBeenCalledTimes(1);
});
it('baselines recovery, same-mode replays, late arrival and hidden/paused intervals', async () => {
	vi.useFakeTimers();
	const system = setup('host-display');
	let current = state();
	system.syncState(current);
	system.start(() => current);
	await Promise.resolve();
	expect(play.mock.calls.filter((c) => c[0] === 'music')).toHaveLength(1);
	system.syncState(current);
	expect(play).toHaveBeenCalledTimes(1);
	system.setConnected(false);
	current = state({ displayPhase: 'answer_reveal' });
	system.syncState(current);
	system.setConnected(true);
	system.syncState(current, { baseline: true });
	expect(play.mock.calls.filter((c) => c[0] === 'reveal')).toHaveLength(0);
	system.syncState(state({ runId: 'two', displayPhase: 'answer_reveal' }));
	expect(play.mock.calls.filter((c) => c[0] === 'reveal')).toHaveLength(0);
	current = state({ runId: 'two', gameState: 'paused' });
	system.syncState(current);
	current = state({ runId: 'two', gameState: 'paused', displayPhase: 'answer_reveal' });
	system.syncState(current);
	Object.defineProperty(document, 'hidden', { configurable: true, value: true });
	document.dispatchEvent(new Event('visibilitychange'));
	vi.advanceTimersByTime(1000);
	Object.defineProperty(document, 'hidden', { configurable: true, value: false });
	document.dispatchEvent(new Event('visibilitychange'));
	expect(play.mock.calls.filter((c) => c[0] === 'reveal')).toHaveLength(0);
	system.dispose();
	expect(dispose).toHaveBeenCalledTimes(1);
});
it('delegates unknown and quiz states and events to the unchanged legacy runtime', () => {
	const system = setup('host-display');
	const quiz = state({ gameType: 'trivia' });
	system.syncState(quiz, { baseline: true });
	system.handleEvent({ type_: 'buzzer_clicked', player_id: 'p' }, quiz);
	expect(legacySync).toHaveBeenCalledWith(quiz, { baseline: true });
	expect(legacyEvent).toHaveBeenCalled();
	expect(play).not.toHaveBeenCalled();
});

it('deduplicates repeated live events using the step and player milestone', async () => {
	const system = setup('host-display');
	const current = state();
	system.syncState(current);
	await Promise.resolve();
	const event = { type_: 'buzzer_clicked', player_id: 'self' } as const;
	system.handleEvent(event, current);
	system.handleEvent(event, current);
	expect(play.mock.calls.filter((call) => call[0] === 'buzz')).toHaveLength(1);
	system.syncState(state({ runId: 'replay' }));
	system.handleEvent(event, state({ runId: 'replay' }));
	expect(play.mock.calls.filter((call) => call[0] === 'buzz')).toHaveLength(2);
});

it('unlocks default sound on interaction and removes activation listeners on disposal', async () => {
	const system = setup('controller');
	activate.mockResolvedValueOnce(false);
	system.syncState(state());
	system.start(() => state());
	await Promise.resolve();
	document.dispatchEvent(new Event('pointerup'));
	await Promise.resolve();
	expect(activate).toHaveBeenCalledTimes(2);
	system.syncState(state({ hasSubmitted: true }));
	expect(play.mock.calls[0][0]).toBe('accepted');
	document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
	expect(activate).toHaveBeenCalledTimes(2);
	system.dispose();
	document.dispatchEvent(new Event('pointerup'));
	document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
	expect(activate).toHaveBeenCalledTimes(2);
});
