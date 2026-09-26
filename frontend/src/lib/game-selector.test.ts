import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Home from '../routes/+page.svelte';
import Create from '../routes/create/+page.svelte';
import { locale } from '$lib/i18n';

const { goto, page } = vi.hoisted(() => ({
	goto: vi.fn(),
	page: { url: new URL('http://localhost/create') }
}));
vi.mock('$app/navigation', () => ({ goto }));
vi.mock('$app/state', () => ({ page }));
vi.mock('$app/environment', () => ({ browser: true }));

const catalog = [
	{
		id: 'trivia',
		localization_key: 'trivia',
		availability: 'available',
		host_modes: ['hosted', 'automatic']
	},
	{
		id: 'price_guessing',
		localization_key: 'priceGuessing',
		availability: 'available',
		host_modes: ['hosted', 'automatic']
	}
];
const definition = { id: 'quiz_demo', title: 'Demo', rounds: [] };
const response = (body: unknown, ok = true) => ({ ok, json: async () => body });
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
	locale.set('en');
	goto.mockReset();
	page.url = new URL('http://localhost/create');
	fetchMock = vi.fn(async (url: string) => {
		if (url === '/api/v1/game-types') return response(catalog);
		if (url === '/api/v1/definitions') return response([definition]);
		if (url === '/api/v1/lobby/create') return response({ join_code: 'ABCDE' });
		return response(definition);
	});
	vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
	cleanup();
	vi.unstubAllGlobals();
});

describe('game selector', () => {
	it('links both playable games and Join', async () => {
		render(Home);
		expect((await screen.findByRole('link', { name: 'Trivia' })).getAttribute('href')).toBe(
			'/create?game=trivia'
		);
		expect(screen.getByRole('link', { name: 'Price Guessing' }).getAttribute('href')).toBe(
			'/create?game=price_guessing'
		);
		expect(screen.getByRole('link', { name: 'Join' }).getAttribute('href')).toBe('/play');
	});

	it('recovers from a catalog request failure', async () => {
		fetchMock.mockRejectedValueOnce(new Error('Offline'));
		render(Home);
		await screen.findByRole('alert');
		await fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
		await screen.findByRole('link', { name: 'Trivia' });
	});

	it.each(['unknown'])('blocks direct setup for %s', async (id) => {
		page.url = new URL(`http://localhost/create?game=${id}`);
		render(Create);
		await screen.findByText('This game is not available yet.');
		expect(screen.queryByRole('button', { name: 'Start Game' })).toBeNull();
	});

	it.each([true, false])('creates Trivia in hosted=%s mode from a legacy URL', async (hosted) => {
		render(Create);
		const start = await screen.findByRole('button', { name: 'Start Game' });
		await waitFor(() => expect((start as HTMLButtonElement).disabled).toBe(false));
		if (!hosted) await fireEvent.click(screen.getByRole('checkbox'));
		await fireEvent.click(start);
		await waitFor(() => expect(goto).toHaveBeenCalledWith('/host/ABCDE'));
		const call = fetchMock.mock.calls.find(([url]) => url === '/api/v1/lobby/create');
		expect(JSON.parse((call as unknown as [string, RequestInit])[1].body as string)).toEqual({
			game_type: 'trivia',
			definition_id: 'quiz_demo',
			host_enabled: hosted
		});
	});

	it('keeps setup available after failed creation and allows retry', async () => {
		render(Create);
		const start = await screen.findByRole('button', { name: 'Start Game' });
		await waitFor(() => expect((start as HTMLButtonElement).disabled).toBe(false));
		fetchMock.mockResolvedValueOnce(response({}, false));
		await fireEvent.click(start);
		await screen.findByText('Could not create the lobby. Please try again.');
		expect(goto).not.toHaveBeenCalled();
		await fireEvent.click(start);
		await waitFor(() => expect(goto).toHaveBeenCalledWith('/host/ABCDE'));
	});

	it('retries setup after a network failure', async () => {
		fetchMock.mockRejectedValueOnce(new Error('Offline'));
		render(Create);
		await screen.findByText('Could not load game packs. Please try again.');
		await fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
		await waitFor(() =>
			expect(
				(screen.getByRole('button', { name: 'Start Game' }) as HTMLButtonElement).disabled
			).toBe(false)
		);
	});

	it('ignores an older preview response after selecting a different pack', async () => {
		let resolveOld: (value: ReturnType<typeof response>) => void = () => {};
		fetchMock.mockImplementation(async (url: string) => {
			if (url === '/api/v1/game-types') return response(catalog);
			if (url === '/api/v1/definitions')
				return response([definition, { ...definition, id: 'second', title: 'Second' }]);
			if (url.endsWith('/quiz_demo'))
				return new Promise<ReturnType<typeof response>>((resolve) => {
					resolveOld = resolve;
				});
			return response({ ...definition, id: 'second', description: 'New pack preview' });
		});
		render(Create);
		await screen.findByRole('combobox');
		await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/definitions/quiz_demo'));
		await fireEvent.change(screen.getByRole('combobox'), { target: { value: 'second' } });
		await screen.findByText('New pack preview');
		resolveOld(response({ ...definition, description: 'Stale pack preview' }));
		await waitFor(() => expect(screen.queryByText('Stale pack preview')).toBeNull());
		expect(screen.getByText('New pack preview')).toBeTruthy();
	});

	it('retries a failed preview before permitting creation', async () => {
		fetchMock.mockImplementation(async (url: string) => {
			if (url === '/api/v1/game-types') return response(catalog);
			if (url === '/api/v1/definitions') return response([definition]);
			return response({}, false);
		});
		render(Create);
		await screen.findByText('Could not load this game pack. Please try again.');
		expect((screen.getByRole('button', { name: 'Start Game' }) as HTMLButtonElement).disabled).toBe(
			true
		);
		fetchMock.mockResolvedValueOnce(response(definition));
		await fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
		await waitFor(() =>
			expect(
				(screen.getByRole('button', { name: 'Start Game' }) as HTMLButtonElement).disabled
			).toBe(false)
		);
	});
});
