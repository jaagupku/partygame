import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { locale } from '$lib/i18n';
import CalorieGameSetup from './CalorieGameSetup.svelte';
import CalorieReveal from './CalorieReveal.svelte';

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
	expect(screen.getByText('45 kcal per 100 ml')).toBeTruthy();
	expect(screen.getByText('50 kcal per 100 ml')).toBeTruthy();
	expect(
		screen.getByRole('link', { name: 'Product data and images: Open Food Facts contributors' })
	).toBeTruthy();
});
