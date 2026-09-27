import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import ContinueGame from './ContinueGame.svelte';
import { locale } from '$lib/i18n';
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
const catalog = [
	{ id: 'price_guessing', localization_key: 'priceGuessing', availability: 'available' }
];
const settings = {
	game_type: 'price_guessing',
	host_enabled: false,
	price_settings: {
		mode: 'guess',
		product_ranges: ['groceries'],
		questions: 5,
		answer_seconds: 45,
		reveal_seconds: 6
	}
};
let posts: unknown[];
let fail: boolean;
beforeEach(() => {
	locale.set('en');
	posts = [];
	fail = false;
	vi.stubGlobal(
		'fetch',
		vi.fn(async (url: string, init?: RequestInit) => {
			if (url.endsWith('/continue')) {
				posts.push(JSON.parse(String(init?.body)));
				return Response.json(fail ? { detail: 'game_archive_failed' } : {}, {
					status: fail ? 503 : 200
				});
			}
			if (url.endsWith('/setup'))
				return Response.json({ run_id: 'run-one', settings, settings_complete: true });
			if (url.endsWith('/availability'))
				return Response.json({
					ranges: [{ product_range: 'groceries', available: true }],
					combinations: [{ mode: 'guess', product_ranges: ['groceries'], questions: 5 }]
				});
			return Response.json(catalog);
		})
	);
});
afterEach(() => {
	cleanup();
	vi.unstubAllGlobals();
});
it('prefills settings, cancels without mutation, and submits edited settings with run identity', async () => {
	const onprepared = vi.fn();
	render(ContinueGame, { lobbyId: 'lobby', onprepared });
	await fireEvent.click(screen.getByRole('button', { name: 'Play again' }));
	await screen.findByLabelText('Questions');
	expect((screen.getByLabelText('Answer time') as HTMLSelectElement).value).toBe('45');
	await fireEvent.click(screen.getByRole('button', { name: 'Back' }));
	expect(posts).toHaveLength(0);
	await fireEvent.click(screen.getByRole('button', { name: 'Play again' }));
	await screen.findByLabelText('Questions');
	await fireEvent.change(screen.getByLabelText('Answer time'), { target: { value: '60' } });
	await fireEvent.click(await screen.findByRole('button', { name: 'Prepare next game' }));
	await waitFor(() => expect(onprepared).toHaveBeenCalledOnce());
	expect(posts[0]).toMatchObject({
		expected_run_id: 'run-one',
		settings: { price_settings: { answer_seconds: 60, reveal_seconds: 6 } }
	});
});
it('keeps edited setup available after archive failure and permits retry', async () => {
	fail = true;
	const onprepared = vi.fn();
	render(ContinueGame, { lobbyId: 'lobby', onprepared });
	await fireEvent.click(screen.getByRole('button', { name: 'Play again' }));
	await screen.findByLabelText('Questions');
	await fireEvent.click(await screen.findByRole('button', { name: 'Prepare next game' }));
	await screen.findByText(/Could not save the finished game/);
	expect(onprepared).not.toHaveBeenCalled();
	fail = false;
	await fireEvent.click(await screen.findByRole('button', { name: 'Prepare next game' }));
	await waitFor(() => expect(onprepared).toHaveBeenCalledOnce());
});
