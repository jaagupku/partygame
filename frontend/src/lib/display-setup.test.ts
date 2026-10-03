import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import Trivia from './components/setup/TriviaGameSetup.svelte';
import Price from './components/prices/PriceGameSetup.svelte';
import Calorie from './components/calories/CalorieGameSetup.svelte';
import Drawing from './components/drawing/DrawingGameSetup.svelte';
import { locale } from './i18n';

const { goto, begin, cancel } = vi.hoisted(() => ({
	goto: vi.fn(),
	begin: vi.fn(),
	cancel: vi.fn()
}));
vi.mock('$app/navigation', () => ({ goto }));
vi.mock('$lib/display-fullscreen', () => ({ beginDisplayFullscreen: begin }));
vi.mock('$app/environment', () => ({ browser: true }));
let creationFails = false;
beforeEach(() => {
	vi.clearAllMocks();
	locale.set('en');
	creationFails = false;
	begin.mockReturnValue(cancel);
	vi.stubGlobal(
		'fetch',
		vi.fn(async (url: string) => {
			let body: unknown;
			if (url === '/api/v1/game-types') body = [{ id: 'trivia', availability: 'available' }];
			else if (url === '/api/v1/definitions') body = [{ id: 'quiz_demo', title: 'Demo' }];
			else if (url.endsWith('/availability'))
				body = {
					ranges: [{ product_range: 'groceries', available: true }],
					combinations: [{ mode: 'mixed', questions: 10, product_ranges: ['groceries'] }]
				};
			else if (url === '/api/v1/lobby/create') {
				expect(begin).toHaveBeenCalledOnce();
				return {
					ok: !creationFails,
					status: creationFails ? 409 : 200,
					json: async () => ({ join_code: 'ABCDE' })
				};
			} else body = { id: 'quiz_demo', title: 'Demo', rounds: [] };
			return { ok: true, json: async () => body };
		})
	);
});
afterEach(() => {
	cleanup();
	vi.unstubAllGlobals();
});
for (const [name, component] of [
	['Trivia', Trivia],
	['Price', Price],
	['Calorie', Calorie],
	['Drawing', Drawing]
] as const) {
	async function start() {
		const button = await screen.findByRole('button', { name: 'Start Game' });
		await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false));
		await fireEvent.click(button);
	}
	it(`${name} enters fullscreen before the request and retains it after navigation`, async () => {
		render(component);
		await start();
		await waitFor(() => expect(goto).toHaveBeenCalledWith('/host/ABCDE'));
		expect(cancel).not.toHaveBeenCalled();
	});
	it(`${name} cancels fullscreen when creation fails`, async () => {
		creationFails = true;
		render(component);
		await start();
		await waitFor(() => expect(cancel).toHaveBeenCalledOnce());
		expect(goto).not.toHaveBeenCalled();
	});
	it(`${name} skips fullscreen for controller continuation`, async () => {
		const onsubmit = vi.fn().mockResolvedValue(undefined);
		render(component, { onsubmit, submitLabel: 'Start Game' });
		await start();
		await waitFor(() => expect(onsubmit).toHaveBeenCalledOnce());
		expect(begin).not.toHaveBeenCalled();
		expect(goto).not.toHaveBeenCalled();
	});
}
