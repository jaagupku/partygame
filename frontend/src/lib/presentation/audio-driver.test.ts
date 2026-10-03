import { afterEach, expect, it, vi } from 'vitest';
import { createBrowserAudioDriver, primePresentationAudio } from './audio-driver';
const contexts: FakeContext[] = [];
class FakeContext {
	state = 'suspended';
	currentTime = 0;
	destination = {};
	resume = vi.fn(async () => {
		this.state = 'running';
	});
	close = vi.fn(async () => {
		this.state = 'closed';
	});
	decodeAudioData = vi.fn(async () => ({}));
	createBufferSource = vi.fn(() => ({
		buffer: null,
		loop: false,
		connect: vi.fn(),
		disconnect: vi.fn(),
		onended: null,
		start: vi.fn(),
		stop: vi.fn()
	}));
	createGain = vi.fn(() => ({
		gain: {
			value: 0,
			cancelScheduledValues: vi.fn(),
			setValueAtTime: vi.fn(),
			linearRampToValueAtTime: vi.fn()
		},
		connect: vi.fn(),
		disconnect: vi.fn()
	}));
	constructor() {
		contexts.push(this);
	}
}
function setup() {
	vi.stubGlobal('AudioContext', FakeContext);
	vi.stubGlobal(
		'fetch',
		vi.fn(async () => ({ ok: true, arrayBuffer: async () => new ArrayBuffer(4) }))
	);
	return createBrowserAudioDriver();
}
afterEach(() => {
	contexts.length = 0;
	vi.unstubAllGlobals();
	vi.useRealTimers();
});
it('reuses Create activation, loads only requested assets and reuses decoded buffers', async () => {
	const driver = setup();
	const cancel = primePresentationAudio();
	expect(contexts).toHaveLength(1);
	expect(fetch).not.toHaveBeenCalled();
	await driver.activate();
	cancel();
	expect(contexts[0].close).not.toHaveBeenCalled();
	const end = vi.fn();
	const error = vi.fn();
	driver.play('one.wav', true, end, error).volume(0.25);
	await vi.waitFor(() => expect(contexts[0].createBufferSource).toHaveBeenCalledTimes(1));
	driver.play('one.wav', false, end, error);
	await vi.waitFor(() => expect(contexts[0].createBufferSource).toHaveBeenCalledTimes(2));
	expect(fetch).toHaveBeenCalledTimes(1);
	driver.dispose();
	expect(contexts[0].close).toHaveBeenCalledTimes(1);
	expect(end).toHaveBeenCalledTimes(2);
	expect(error).not.toHaveBeenCalled();
});
it('cancels late loads and fade timers after leaving the screen', async () => {
	vi.useFakeTimers();
	const driver = setup();
	await driver.activate();
	let release!: (value: unknown) => void;
	vi.mocked(fetch).mockImplementation(
		() =>
			new Promise((resolve) => {
				release = resolve as typeof release;
			})
	);
	const end = vi.fn();
	const error = vi.fn();
	const voice = driver.play('slow.wav', true, end, error);
	voice.stop(0.35);
	driver.dispose();
	release({ ok: true, arrayBuffer: async () => new ArrayBuffer(4) });
	await vi.runAllTimersAsync();
	expect(contexts[0].createBufferSource).not.toHaveBeenCalled();
	expect(end).toHaveBeenCalledTimes(1);
	expect(error).not.toHaveBeenCalled();
	expect(await driver.activate()).toBe(false);
});
it('reports failed loads and permits a new request on explicit retry', async () => {
	const driver = setup();
	await driver.activate();
	const error = vi.fn();
	vi.mocked(fetch).mockResolvedValueOnce({ ok: false } as Response);
	driver.play('missing.wav', true, vi.fn(), error);
	await vi.waitFor(() => expect(error).toHaveBeenCalledTimes(1));
	driver.play('missing.wav', true, vi.fn(), error);
	await vi.waitFor(() => expect(contexts[0].createBufferSource).toHaveBeenCalledTimes(1));
	driver.dispose();
});
