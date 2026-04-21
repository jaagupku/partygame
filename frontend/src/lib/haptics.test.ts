import { afterEach, describe, expect, it, vi } from 'vitest';

import { triggerBuzzerHapticPulse } from '$lib/haptics.js';

describe('triggerBuzzerHapticPulse', () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('requests a short vibration when the API is available', () => {
		const vibrate = vi.fn(() => true);
		Object.defineProperty(window.navigator, 'vibrate', {
			configurable: true,
			value: vibrate
		});

		expect(triggerBuzzerHapticPulse()).toBe(true);
		expect(vibrate).toHaveBeenCalledWith(30);
	});

	it('returns false when the vibration API is unavailable', () => {
		Object.defineProperty(window.navigator, 'vibrate', {
			configurable: true,
			value: undefined
		});

		expect(triggerBuzzerHapticPulse()).toBe(false);
	});

	it('does not vibrate for non-positive durations', () => {
		const vibrate = vi.fn(() => true);
		Object.defineProperty(window.navigator, 'vibrate', {
			configurable: true,
			value: vibrate
		});

		expect(triggerBuzzerHapticPulse(0)).toBe(false);
		expect(vibrate).not.toHaveBeenCalled();
	});
});
