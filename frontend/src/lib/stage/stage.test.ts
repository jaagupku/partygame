import { expect, it } from 'vitest';
import { STAGE_HEIGHT, STAGE_WIDTH, stageScale } from './stage';

it('keeps a 16:9 design size', () => {
	expect(STAGE_WIDTH / STAGE_HEIGHT).toBeCloseTo(16 / 9);
});
it('scales uniformly to fill a 16:9 area', () => {
	expect(stageScale(1920, 1080)).toBe(1);
	expect(stageScale(1280, 720)).toBeCloseTo(2 / 3);
	expect(stageScale(3840, 2160)).toBe(2);
});
it('fits the limiting side on other aspect ratios', () => {
	// Ultrawide: bars left and right.
	expect(stageScale(2560, 1080)).toBe(1);
	// Tall or narrow window: bars above and below.
	expect(stageScale(960, 1100)).toBe(0.5);
});
it('hides the stage until the area has been measured', () => {
	expect(stageScale(0, 0)).toBe(0);
	expect(stageScale(1920, 0)).toBe(0);
	expect(stageScale(Number.NaN, 1080)).toBe(0);
});
