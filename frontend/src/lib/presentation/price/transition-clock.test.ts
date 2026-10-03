import { expect, it } from 'vitest';
import { createPriceTransitionClock } from './transition-clock';
it('resumes at server elapsed time and never rewinds on repeated snapshots', () => {
	const clock = createPriceTransitionClock();
	const transition = { id: 'run:step', duration_ms: 600, elapsed_ms: 250 };
	expect(clock.sync(transition, 1000)).toBe(250);
	expect(clock.read(1100)).toBe(350);
	expect(clock.sync(transition, 1100)).toBe(350);
	expect(clock.sync({ ...transition, elapsed_ms: 550 }, 1150)).toBe(550);
	expect(clock.read(2000)).toBe(600);
	expect(clock.sync({ ...transition, id: 'run:next', elapsed_ms: 0 }, 2100)).toBe(0);
	expect(clock.read(2150)).toBe(50);
});
it('skips elapsed transitions and handles late arrivals without extra waiting', () => {
	const clock = createPriceTransitionClock();
	expect(clock.sync({ id: 'late', duration_ms: 600, elapsed_ms: 900 }, 50)).toBe(600);
});
