import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { locale } from '$lib/i18n';
import PriceGameSetup from './PriceGameSetup.svelte';
import PriceReveal from './PriceReveal.svelte';
import PlayerInputPanel from '../controller/PlayerInputPanel.svelte';

const { goto } = vi.hoisted(() => ({ goto: vi.fn() }));
vi.mock('$app/navigation', () => ({ goto }));
vi.mock('$app/environment', () => ({ browser: true }));
const modes = ['guess', 'compare', 'mixed'];
const ranges = ['groceries', 'electronics', 'both'];
const availability = {
	ranges: ranges.slice(0, 2).map((product_range) => ({
		product_range,
		available: true,
		captured_at: '2026-09-19T00:00:00Z'
	})),
	combinations: modes.flatMap((mode) =>
		ranges.flatMap((product_range) =>
			[5, 10, 15, 20].map((questions) => ({ mode, product_range, questions }))
		)
	)
};
const cards = [
	{ id: '0', title: 'Milk 1l', detail: '1l', image_url: '/api/v1/media/milk' },
	{ id: '1', title: 'Cheese 500g', detail: '500g', image_url: '/api/v1/media/cheese' }
];
function step(mode: 'guess' | 'compare'): RuntimeStepState {
	return {
		id: 's1',
		title: 'Price',
		input_kind: mode === 'guess' ? 'number' : 'radio',
		input_enabled: true,
		input_options: mode === 'guess' ? [] : ['0', '1'],
		price_mode: mode,
		price_products: mode === 'guess' ? cards.slice(0, 1) : cards,
		price_reveal: [],
		price_results: [],
		evaluation_type: mode === 'guess' ? 'price_closeness' : 'exact_text',
		evaluation_points: 1000,
		max_points: 1000,
		timer: { seconds: 30, enforced: true }
	} as RuntimeStepState;
}
function panel(activeStep: RuntimeStepState) {
	const submit = vi.fn();
	render(PlayerInputPanel, {
		activeStep,
		baseInputDisabled: false,
		buzzerActive: false,
		canContinueHostlessInfoSlide: false,
		disabledBuzzerPlayerIds: [],
		displayPhase: 'question_active',
		drawingItems: [],
		drawingVotedPlayerIds: [],
		hasSubmitted: false,
		playerId: 'p1',
		onContinueInfoSlide: vi.fn(),
		onSubmitAnswer: submit,
		onSubmitDrawingVote: vi.fn()
	});
	return submit;
}
beforeEach(() => {
	locale.set('en');
	goto.mockReset();
});
afterEach(() => {
	cleanup();
	vi.unstubAllGlobals();
});

describe('price game', () => {
	it('disables launch when no dataset exists and retries', async () => {
		const fetch = vi
			.fn()
			.mockResolvedValueOnce({ ok: true, json: async () => ({ ranges: [], combinations: [] }) })
			.mockResolvedValue({ ok: true, json: async () => availability });
		vi.stubGlobal('fetch', fetch);
		render(PriceGameSetup);
		const start = await screen.findByRole('button', { name: 'Start Game' });
		expect((start as HTMLButtonElement).disabled).toBe(true);
		await fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
		await waitFor(() =>
			expect(
				(screen.getByRole('button', { name: 'Start Game' }) as HTMLButtonElement).disabled
			).toBe(false)
		);
	});
	it.each(modes)('creates %s with chosen settings and no quiz definition', async (mode) => {
		const fetch = vi
			.fn()
			.mockResolvedValueOnce({ ok: true, json: async () => availability })
			.mockResolvedValueOnce({ ok: true, json: async () => ({ join_code: 'ABCDE' }) });
		vi.stubGlobal('fetch', fetch);
		render(PriceGameSetup);
		await screen.findByLabelText('Question mode');
		await fireEvent.change(screen.getByLabelText('Question mode'), { target: { value: mode } });
		await fireEvent.click(screen.getByRole('button', { name: 'Start Game' }));
		await waitFor(() => expect(goto).toHaveBeenCalledWith('/host/ABCDE'));
		expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({
			game_type: 'price_guessing',
			host_enabled: false,
			price_settings: { mode, product_range: 'both', questions: 10, answer_seconds: 30 }
		});
	});
	it('accepts decimal comma and rejects too much precision', async () => {
		const submit = panel(step('guess'));
		const input = screen.getByLabelText('Your price (€)');
		await fireEvent.input(input, { target: { value: '1.001' } });
		expect(
			(screen.getByRole('button', { name: 'Submit price' }) as HTMLButtonElement).disabled
		).toBe(true);
		await fireEvent.input(input, { target: { value: '1,25' } });
		await fireEvent.click(screen.getByRole('button', { name: 'Submit price' }));
		expect(submit).toHaveBeenCalledWith('1.25');
	});
	it('submits stable card IDs instead of titles', async () => {
		const submit = panel(step('compare'));
		await fireEvent.click(screen.getByRole('button', { name: /Cheese 500g/ }));
		expect(submit).toHaveBeenCalledWith('1');
	});
	it('shows no prices or source links before reveal', () => {
		render(PriceReveal, { step: step('guess') });
		expect(screen.queryByRole('link')).toBeNull();
		expect(screen.queryByText('Answers and points')).toBeNull();
	});
	it('renders recorded prices, source attribution and all player results', () => {
		const value = step('guess');
		value.price_reveal = [
			{
				id: '0',
				price_minor: 125,
				retailer: 'rimi',
				source_url: 'https://www.rimi.ee/product',
				captured_at: '2026-09-19T00:00:00Z'
			}
		];
		value.price_results = [
			{ player_id: 'p1', player_name: 'Alice', answer: '1.25', points: 1000 },
			{ player_id: 'p2', player_name: 'Bob', answer: null, points: 0 }
		];
		render(PriceReveal, { step: value });
		expect(screen.getAllByText('€1.25').length).toBe(2);
		expect(screen.getByText('No answer')).toBeTruthy();
		expect(screen.getByRole('link', { name: 'View product' }).getAttribute('href')).toBe(
			'https://www.rimi.ee/product'
		);
		expect(screen.getByText(/\+1000/)).toBeTruthy();
	});
});
