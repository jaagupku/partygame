import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/svelte';
import CountUp from './CountUp.svelte';
import { COUNT_UP_DELAY_MS, COUNT_UP_MS, countUpValue } from './guess-reveal';

afterEach(cleanup);

describe('count-up reveal', () => {
	it('holds under the reveal sting, then eases in to land exactly on the value', () => {
		expect(countUpValue(44999, 0)).toBe(0);
		expect(countUpValue(44999, COUNT_UP_DELAY_MS)).toBe(0);
		// Half the time covers only an eighth of the distance (t³).
		expect(countUpValue(1000, COUNT_UP_DELAY_MS + COUNT_UP_MS / 2)).toBe(125);
		expect(countUpValue(44999, COUNT_UP_DELAY_MS + COUNT_UP_MS)).toBe(44999);
		expect(countUpValue(44999, 10_000)).toBe(44999);
	});
	it('starts from zero only on a live reveal', () => {
		const format = (value: number) => `${value} kcal`;
		const live = render(CountUp, { value: 250, format, animate: true });
		expect(live.container.querySelector('[aria-hidden="true"]')?.textContent).toBe('0 kcal');
		expect(live.container.querySelector('.sr-only')?.textContent).toBe('250 kcal');
		cleanup();
		const settled = render(CountUp, { value: 250, format });
		expect(settled.container.textContent).toBe('250 kcal');
	});
});
