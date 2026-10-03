import { afterEach, expect, it, vi } from 'vitest';
import { idleCursor } from './idle-cursor';
afterEach(() => vi.useRealTimers());
it('hides after two seconds, reveals on movement/click, and cleans up on leaving gameplay', () => {
	vi.useFakeTimers();
	const node = document.createElement('div');
	const action = idleCursor(node);
	vi.advanceTimersByTime(1999);
	expect(node.hasAttribute('data-cursor-idle')).toBe(false);
	vi.advanceTimersByTime(1);
	expect(node.hasAttribute('data-cursor-idle')).toBe(true);
	for (const type of ['mousemove', 'mousedown']) {
		window.dispatchEvent(new MouseEvent(type));
		expect(node.hasAttribute('data-cursor-idle')).toBe(false);
		vi.advanceTimersByTime(2000);
		expect(node.hasAttribute('data-cursor-idle')).toBe(true);
	}
	action.destroy();
	expect(node.hasAttribute('data-cursor-idle')).toBe(false);
	window.dispatchEvent(new MouseEvent('mousemove'));
	vi.advanceTimersByTime(2000);
	expect(node.hasAttribute('data-cursor-idle')).toBe(false);
	expect(vi.getTimerCount()).toBe(0);
});
