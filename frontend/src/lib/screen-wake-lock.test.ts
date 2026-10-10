import { afterEach, expect, it, vi } from 'vitest';
import { screenWakeLock } from './screen-wake-lock';

function fakeWakeLock() {
	const locks: (EventTarget & { released: boolean; release: () => Promise<void> })[] = [];
	const request = vi.fn(async () => {
		const lock = Object.assign(new EventTarget(), {
			released: false,
			async release() {
				lock.released = true;
				lock.dispatchEvent(new Event('release'));
			}
		});
		locks.push(lock);
		return lock;
	});
	Object.defineProperty(navigator, 'wakeLock', { value: { request }, configurable: true });
	return { request, locks };
}
function setVisibility(state: DocumentVisibilityState) {
	Object.defineProperty(document, 'visibilityState', { value: state, configurable: true });
	document.dispatchEvent(new Event('visibilitychange'));
}
const flush = () => new Promise((resolve) => setTimeout(resolve));

afterEach(() => {
	Reflect.deleteProperty(navigator, 'wakeLock');
	Reflect.deleteProperty(document, 'visibilityState');
});

it('holds one screen lock during gameplay, renews it after the tab returns, and releases it', async () => {
	const { request, locks } = fakeWakeLock();
	const action = screenWakeLock(document.createElement('div'));
	await flush();
	expect(request).toHaveBeenCalledTimes(1);
	expect(request).toHaveBeenCalledWith('screen');

	// The browser releases the lock when the tab is hidden; it is not re-requested while hidden.
	setVisibility('hidden');
	await locks[0].release();
	await flush();
	expect(request).toHaveBeenCalledTimes(1);
	setVisibility('visible');
	await flush();
	setVisibility('visible');
	await flush();
	expect(request).toHaveBeenCalledTimes(2);

	action.destroy();
	expect(locks[1].released).toBe(true);
	setVisibility('visible');
	await flush();
	expect(request).toHaveBeenCalledTimes(2);
});

it('is a no-op where the API is missing or refused', async () => {
	expect(() => screenWakeLock(document.createElement('div')).destroy()).not.toThrow();
	Object.defineProperty(navigator, 'wakeLock', {
		value: { request: vi.fn().mockRejectedValue(new DOMException('denied', 'NotAllowedError')) },
		configurable: true
	});
	const action = screenWakeLock(document.createElement('div'));
	await flush();
	action.destroy();
});
