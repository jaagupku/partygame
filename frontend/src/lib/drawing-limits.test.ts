import { describe, expect, it } from 'vitest';
import { DRAWING_LIMITS, getDrawingLimitUsage } from './drawing-limits';

function drawingWithCounts(strokeCount: number, pointsPerStroke: number): DrawingSubmission {
	return {
		w: 512,
		h: 384,
		s: Array.from({ length: strokeCount }, () => [
			0,
			8,
			0,
			Array.from({ length: pointsPerStroke }, (_, index) => [
				Math.round(((index % 20) / 20) * 512),
				Math.round((index / Math.max(pointsPerStroke, 1)) * 384)
			]).flat()
		])
	};
}

describe('drawing limits', () => {
	it('allows drawings at the expanded stroke and point limits', () => {
		const usage = getDrawingLimitUsage(drawingWithCounts(DRAWING_LIMITS.maxStrokes, 20));

		expect(usage.strokes).toBe(DRAWING_LIMITS.maxStrokes);
		expect(usage.points).toBe(DRAWING_LIMITS.maxPoints);
		expect(usage.overLimit).toBe(false);
		expect(usage.nearLimit).toBe(true);
	});

	it('blocks drawings beyond the expanded stroke limit', () => {
		const usage = getDrawingLimitUsage(drawingWithCounts(DRAWING_LIMITS.maxStrokes + 1, 1));

		expect(usage.overLimit).toBe(true);
	});

	it('blocks drawings beyond the expanded point limit', () => {
		const usage = getDrawingLimitUsage(drawingWithCounts(DRAWING_LIMITS.maxStrokes, 21));

		expect(usage.points).toBeGreaterThan(DRAWING_LIMITS.maxPoints);
		expect(usage.overLimit).toBe(true);
	});
});
