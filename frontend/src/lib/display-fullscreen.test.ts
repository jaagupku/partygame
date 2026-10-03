import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { beginDisplayFullscreen, exitDisplayFullscreen } from './display-fullscreen';

let fullscreen: Element | null;
let request: ReturnType<typeof vi.fn>;
let exit: ReturnType<typeof vi.fn>;
beforeEach(() => {
	fullscreen = null;
	request = vi.fn(async () => {
		fullscreen = document.documentElement;
	});
	exit = vi.fn(async () => {
		fullscreen = null;
	});
	Object.defineProperty(document, 'fullscreenElement', {
		configurable: true,
		get: () => fullscreen
	});
	Object.defineProperty(document.documentElement, 'requestFullscreen', {
		configurable: true,
		value: request
	});
	Object.defineProperty(document, 'exitFullscreen', { configurable: true, value: exit });
});
afterEach(() => {
	exitDisplayFullscreen();
	vi.restoreAllMocks();
});
it('requests synchronously, retains fullscreen, and exits on display teardown', async () => {
	beginDisplayFullscreen();
	expect(request).toHaveBeenCalledOnce();
	await Promise.resolve();
	expect(exit).not.toHaveBeenCalled();
	exitDisplayFullscreen();
	expect(exit).toHaveBeenCalledOnce();
});
it('leaves pre-existing fullscreen alone', async () => {
	fullscreen = document.documentElement;
	const cancel = beginDisplayFullscreen();
	cancel();
	exitDisplayFullscreen();
	expect(request).not.toHaveBeenCalled();
	expect(exit).not.toHaveBeenCalled();
});
it.each(['rejected', 'unsupported', 'throws'])('tolerates %s requests', async (kind) => {
	if (kind === 'rejected') request.mockRejectedValue(new Error('Denied'));
	if (kind === 'throws')
		request.mockImplementation(() => {
			throw new Error('Denied');
		});
	if (kind === 'unsupported')
		Object.defineProperty(document.documentElement, 'requestFullscreen', { value: undefined });
	const cancel = beginDisplayFullscreen();
	await Promise.resolve();
	cancel();
	expect(exit).not.toHaveBeenCalled();
});
it('undoes a delayed fullscreen request after creation fails', async () => {
	let resolve!: () => void;
	request.mockImplementation(
		() =>
			new Promise<void>((done) => {
				resolve = done;
			})
	);
	const cancel = beginDisplayFullscreen();
	cancel();
	fullscreen = document.documentElement;
	resolve();
	await Promise.resolve();
	expect(exit).toHaveBeenCalledOnce();
});
it('undoes successful fullscreen when creation fails', async () => {
	const cancel = beginDisplayFullscreen();
	await Promise.resolve();
	cancel();
	expect(exit).toHaveBeenCalledOnce();
});
it('respects Escape and does not own a later manual fullscreen session', async () => {
	beginDisplayFullscreen();
	await Promise.resolve();
	fullscreen = null;
	document.dispatchEvent(new Event('fullscreenchange'));
	fullscreen = document.documentElement;
	exitDisplayFullscreen();
	expect(request).toHaveBeenCalledOnce();
	expect(exit).not.toHaveBeenCalled();
});
