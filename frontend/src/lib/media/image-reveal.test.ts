import { describe, expect, it } from 'vitest';
import { mapRevealProgress, normalizeRevealCurve } from './image-reveal';

describe('image reveal curves', () => {
	it('defaults to linear progress when no curve is stored', () => {
		expect(mapRevealProgress(0.25)).toBeCloseTo(0.25, 5);
		expect(mapRevealProgress(0.75, [0, 0, 1, 1])).toBeCloseTo(0.75, 5);
	});

	it('clamps progress and curve values to the 0..1 range', () => {
		expect(mapRevealProgress(-1)).toBe(0);
		expect(mapRevealProgress(2)).toBe(1);
		expect(normalizeRevealCurve([-0.2, 0.4, 1.4, 0.8])).toEqual([0, 0.4, 1, 0.8]);
	});

	it('maps progress through non-linear cubic-bezier curves', () => {
		expect(mapRevealProgress(0.25, [0.5, 0, 1, 1])).toBeLessThan(0.25);
		expect(mapRevealProgress(0.75, [0, 0, 0.5, 1])).toBeGreaterThan(0.75);
	});
});
