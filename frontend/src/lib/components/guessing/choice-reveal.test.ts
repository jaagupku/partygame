import { cleanup, render } from '@testing-library/svelte';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { locale } from '$lib/i18n';
import QuestionCard from '../QuestionCard.svelte';
import CalorieReveal from '../calories/CalorieReveal.svelte';
import ChoiceReveal from './ChoiceReveal.svelte';
import { choiceRevealMs, choiceTrays, choiceWinner } from './guess-reveal';

const result = (id: string, answer: unknown, points = 0): PriceResult => ({
	player_id: id,
	player_name: id,
	answer,
	points
});
const products = [
	{ id: '0', title: 'Oats', basis: '100g' },
	{ id: '1', title: 'Rice', basis: '100g' }
] as CalorieCard[];
const values = [
	{ id: '0', value: '380', unit: 'kcal' },
	{ id: '1', value: '350', unit: 'kcal' }
];
const results = [
	result('Ann', '0', 1000),
	result('Ben', '1'),
	result('Cid', 0, 1000),
	result('Dee', null)
];

beforeEach(() => locale.set('en'));
afterEach(() => {
	cleanup();
	vi.useRealTimers();
	Reflect.deleteProperty(HTMLElement.prototype, 'animate');
});

it('picks the first highest value like the generator and groups answers by product', () => {
	expect(
		choiceWinner([
			{ id: '0', value: 5 },
			{ id: '1', value: 5 }
		])
	).toBe('0');
	expect(
		choiceWinner([
			{ id: '0', value: 4 },
			{ id: '1', value: 5 }
		])
	).toBe('1');
	const { trays, pool } = choiceTrays(results, ['0', '1']);
	expect(trays.get('0')!.map((r) => r.player_id)).toEqual(['Ann', 'Cid']);
	expect(trays.get('1')!.map((r) => r.player_id)).toEqual(['Ben']);
	expect(pool.map((r) => r.player_id)).toEqual(['Dee']);
	// Three players hop one at a time; a bigger lobby shares a capped budget.
	expect(choiceRevealMs(results, ['0', '1'])).toBe(500 + 2 * 520 + 400 + 350);
	const crowd = Array.from({ length: 30 }, (_, i) => result(`P${i}`, String(i % 2)));
	expect(choiceRevealMs(crowd, ['0', '1'])).toBeLessThan(6000);
});

it('shows the final placement and winner immediately when not animating', () => {
	const view = render(ChoiceReveal, {
		products,
		values,
		correctId: '0',
		results,
		winnerLabel: 'More calories'
	});
	const [oats, rice] = view.container.querySelectorAll('.choice-option');
	expect(view.container.querySelector('.choice-revealed')).toBeTruthy();
	expect(oats.classList).toContain('choice-correct');
	expect(rice.classList).toContain('choice-wrong');
	expect(oats.querySelectorAll('.choice-player')).toHaveLength(2);
	expect(rice.querySelectorAll('.choice-player')).toHaveLength(1);
	// Only the player without an answer stays in the lineup.
	expect(view.container.querySelectorAll('.choice-lineup .choice-player')).toHaveLength(1);
	expect(view.container.querySelector('.choice-slot')).toBeNull();
	expect(oats.querySelector('.choice-ribbon')?.getAttribute('aria-hidden')).toBe('false');
});

it('hops players from the lineup one at a time, then reveals the winner and cleans up', async () => {
	vi.useFakeTimers();
	const cancel = vi.fn();
	const animate = vi.fn((_keyframes: Keyframe[], _options: KeyframeAnimationOptions) => ({
		cancel
	}));
	Object.defineProperty(HTMLElement.prototype, 'animate', { value: animate, configurable: true });
	const view = render(ChoiceReveal, {
		products,
		values,
		correctId: '0',
		results,
		winnerLabel: 'More calories',
		animate: true
	});
	// Three hops, three card bumps on landing and one pop for the player who stays.
	expect(animate).toHaveBeenCalledTimes(7);
	expect(view.container.querySelectorAll('.choice-slot')).toHaveLength(3);
	const hopDurations = animate.mock.calls
		.map(([, options]) => options)
		.filter((options) => options.fill === 'backwards' && !options.delay)
		.map((options) => Number(options.duration));
	expect(hopDurations).toEqual([...hopDurations].sort((a, b) => a - b));
	expect(new Set(hopDurations).size).toBe(3);
	expect(view.container.querySelector('.choice-revealed')).toBeNull();
	expect(view.container.querySelector('.choice-correct')).toBeNull();
	await vi.advanceTimersByTimeAsync(choiceRevealMs(results, ['0', '1']));
	expect(view.container.querySelector('.choice-correct')).toBeTruthy();
	expect(view.container.querySelector('.choice-player-missing')).toBeTruthy();
	view.unmount();
	expect(cancel).toHaveBeenCalledTimes(7);
});

function compareStep(reveal: boolean): RuntimeStepState {
	return {
		id: 'calorie-compare',
		title: 'Calories',
		input_kind: 'radio',
		input_enabled: !reveal,
		input_options: ['0', '1'],
		calorie_mode: 'compare',
		calorie_products: products,
		calorie_reveal: reveal
			? [
					{
						id: '0',
						kcal: 380,
						basis: '100g',
						captured_at: '2026-09-27',
						source_url: 'https://world.openfoodfacts.org'
					},
					{
						id: '1',
						kcal: 350,
						basis: '100g',
						captured_at: '2026-09-27',
						source_url: 'https://world.openfoodfacts.org'
					}
				]
			: [],
		calorie_results: reveal ? results : [],
		evaluation_type: 'exact_text',
		evaluation_points: 1000,
		max_points: 1000,
		timer: { seconds: 30, enforced: true }
	} as unknown as RuntimeStepState;
}

it('animates only a reveal that followed the live question on the display', async () => {
	vi.useFakeTimers();
	const live = render(QuestionCard, {
		step: compareStep(false),
		displayPhase: 'question_active',
		choiceReveal: true
	});
	await live.rerender({ step: compareStep(true), displayPhase: 'answer_reveal' });
	expect(live.container.querySelector('.choice-reveal')).toBeTruthy();
	expect(live.container.querySelector('.choice-revealed')).toBeNull();
	// The coach waits for the correct product before reacting.
	expect(live.container.querySelector('.studio-coach p')).toBeNull();
	await vi.advanceTimersByTimeAsync(choiceRevealMs(results, ['0', '1']));
	expect(live.container.querySelector('.choice-revealed')).toBeTruthy();
	expect(live.container.querySelector('.studio-coach p')).toBeTruthy();
	live.unmount();

	const reconnected = render(QuestionCard, {
		step: compareStep(true),
		displayPhase: 'answer_reveal',
		choiceReveal: true
	});
	expect(reconnected.container.querySelector('.choice-revealed')).toBeTruthy();
	expect(reconnected.container.querySelector('.studio-coach p')).toBeTruthy();
});

it('marks the winning product on phones without the display animation', () => {
	const view = render(CalorieReveal, {
		step: compareStep(true),
		playerId: 'Ann',
		showCoach: false
	});
	expect(view.container.querySelector('.choice-reveal')).toBeNull();
	const winner = view.container.querySelector('.guess-reveal-correct');
	expect(winner?.textContent).toContain('More calories');
	expect(winner?.textContent).toContain('Oats');
	expect(view.container.querySelectorAll('.guess-reveal-other')).toHaveLength(1);
});
