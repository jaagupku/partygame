import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { locale } from '$lib/i18n';
import CalorieGameSetup from './CalorieGameSetup.svelte';
import CalorieReveal from './CalorieReveal.svelte';
import QuestionCard from '../QuestionCard.svelte';

const { goto } = vi.hoisted(() => ({ goto: vi.fn() }));
vi.mock('$app/navigation', () => ({ goto }));
vi.mock('$app/environment', () => ({ browser: true }));
beforeEach(() => {
	locale.set('en');
	goto.mockReset();
});
afterEach(() => {
	cleanup();
	vi.unstubAllGlobals();
});
it.each(['guess', 'compare', 'mixed'])(
	'creates %s calorie game without price settings',
	async (mode) => {
		const fetch = vi
			.fn()
			.mockResolvedValueOnce({
				ok: true,
				json: async () => ({ combinations: [{ mode, questions: 10 }] })
			})
			.mockResolvedValueOnce({ ok: true, json: async () => ({ join_code: 'ABCDE' }) });
		vi.stubGlobal('fetch', fetch);
		render(CalorieGameSetup);
		await screen.findByLabelText('Question mode');
		await fireEvent.change(screen.getByLabelText('Question mode'), { target: { value: mode } });
		await fireEvent.click(screen.getByRole('button', { name: 'Start Game' }));
		await waitFor(() => expect(goto).toHaveBeenCalledWith('/host/ABCDE'));
		expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({
			game_type: 'calorie_guessing',
			host_enabled: false,
			calorie_settings: { mode, questions: 10, answer_seconds: 30, reveal_seconds: 4 }
		});
	}
);
it('renders recorded whole kcal with volume units and attribution', () => {
	render(CalorieReveal, {
		step: {
			calorie_mode: 'guess',
			calorie_products: [
				{ id: '0', title: 'Juice', basis: '100ml', detail: '1 l', image_url: '/image' }
			],
			calorie_reveal: [
				{
					id: '0',
					kcal: 45,
					basis: '100ml',
					captured_at: '2026-09-27',
					source_url: 'https://world.openfoodfacts.org/product/12345678'
				}
			],
			calorie_results: [{ player_id: 'p', player_name: 'Player', answer: '50', points: 889 }]
		} as RuntimeStepState
	});
	expect(screen.getByText('45').parentElement?.textContent).toMatch(/45\s+kcal per 100 ml/);
	expect(screen.getByText('50 kcal per 100 ml')).toBeTruthy();
	expect(
		screen.getByRole('link', { name: 'Product data and images: Open Food Facts contributors' })
	).toBeTruthy();
});

it('reveals closest calorie guesses first, keeps missing answers last, and preserves rows on snapshots', async () => {
	const row = (name: string, answer: unknown, points = 0): PriceResult => ({
		player_id: name,
		player_name: name,
		answer,
		points
	});
	const step = {
		id: 'calorie-1',
		calorie_mode: 'guess',
		calorie_products: [{ id: '0', title: 'Food', basis: '100g' }],
		calorie_reveal: [
			{
				id: '0',
				kcal: 100,
				basis: '100g',
				captured_at: '2026-09-27',
				source_url: 'https://world.openfoodfacts.org'
			}
		],
		calorie_results: [
			row('Missing', null),
			row('Far', 900),
			row('Near', 300),
			row('Under', 99, 990),
			row('Over', 101, 990),
			row('Exact', 100, 1000),
			row('Zero', 0)
		]
	} as RuntimeStepState;
	const view = render(CalorieReveal, { step });
	const rows = () =>
		[...view.container.querySelectorAll('.guess-result-player .font-bold')].map(
			(node) => node.textContent
		);
	expect(rows()).toEqual(['Exact', 'Under', 'Over', 'Zero', 'Near', 'Far', 'Missing']);
	expect(view.container.querySelector('details')).toBeNull();
	expect(screen.getByRole('link', { name: 'View product' })).toBeTruthy();
	const first = view.container.querySelector('li');
	const last = view.container.querySelector('li:last-child') as HTMLElement;
	expect(first?.getAttribute('style')).toContain('450ms');
	expect(Number.parseFloat(last.style.getPropertyValue('--reveal-delay'))).toBeGreaterThan(450);
	await view.rerender({
		step: { ...step, calorie_results: step.calorie_results?.map((r) => ({ ...r })) }
	});
	expect(view.container.querySelector('li')).toBe(first);
	await view.rerender({
		step: {
			...step,
			calorie_mode: 'compare',
			calorie_results: [row('Missing', null), row('Wrong', '1'), row('Right', '0', 1000)]
		}
	});
	expect(rows()).toEqual(['Right', 'Wrong', 'Missing']);
});

it('shows one coach on the display while answering and during the reveal', async () => {
	const step = {
		id: 'calorie-coach',
		title: 'Calories',
		input_kind: 'number',
		input_enabled: true,
		input_options: [],
		calorie_mode: 'guess',
		calorie_products: [{ id: '0', title: 'Food', basis: '100g' }],
		calorie_reveal: [],
		calorie_results: [],
		evaluation_points: 1000,
		max_points: 1000,
		timer: { seconds: 30, enforced: true }
	} as unknown as RuntimeStepState;
	const view = render(QuestionCard, { step, displayPhase: 'question_active' });
	expect(view.container.querySelectorAll('.studio-coach')).toHaveLength(1);
	await view.rerender({
		step: {
			...step,
			calorie_reveal: [
				{
					id: '0',
					kcal: 100,
					basis: '100g',
					captured_at: '2026-09-27',
					source_url: 'https://world.openfoodfacts.org'
				}
			],
			calorie_results: [{ player_id: 'p', player_name: 'P', answer: '95', points: 950 }]
		} as RuntimeStepState,
		displayPhase: 'answer_reveal'
	});
	const coaches = view.container.querySelectorAll('.studio-coach');
	expect(coaches).toHaveLength(1);
	expect(coaches[0].getAttribute('data-coach-pose')).toBe('celebrate');
	await view.rerender({ showCoach: false });
	expect(view.container.querySelectorAll('.studio-coach')).toHaveLength(0);
});

it('separates comparison titles from their capture dates', () => {
	const item = (id: string) => ({
		id,
		kcal: 100,
		basis: '100g' as const,
		captured_at: '2026-09-27',
		source_url: 'https://world.openfoodfacts.org'
	});
	const view = render(CalorieReveal, {
		step: {
			id: 'calorie-compare',
			calorie_mode: 'compare',
			calorie_products: [
				{ id: '0', title: 'Oats', basis: '100g' },
				{ id: '1', title: 'Rice', basis: '100g' }
			],
			calorie_reveal: [item('0'), item('1')],
			calorie_results: []
		} as unknown as RuntimeStepState
	});
	expect(view.container.querySelector('.calorie-product-details li')?.textContent).toMatch(
		/Oats · Nutrition recorded/
	);
});
