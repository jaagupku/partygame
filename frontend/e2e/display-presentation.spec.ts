import { expect, test, type WebSocketRoute } from '@playwright/test';

// Isolated API/socket fixtures exercise the real display without creating stored lobbies.
test('fullscreen survives creation and cursor follows the display lifecycle', async ({ page }) => {
	const errors: string[] = [];
	page.on('pageerror', (error) => errors.push(error.message));
	await page.addInitScript(() => localStorage.setItem('partygame-locale', JSON.stringify('en')));
	const lobby = {
		id: 'display-test',
		run_id: 'display-run',
		join_code: 'ABCDE',
		game_type: 'trivia',
		definition_id: 'quiz_demo',
		definition_title: 'Display test',
		state: 'waiting_for_players',
		host_enabled: false,
		players: []
	};
	const definition = { id: 'quiz_demo', title: 'Display test', rounds: [] };
	await page.route('**/api/**', async (route) => {
		const path = new URL(route.request().url()).pathname;
		let json: unknown = {};
		if (path === '/api/v1/auth/me') json = null;
		else if (path === '/api/v1/game-types') json = [{ id: 'trivia', availability: 'available' }];
		else if (path === '/api/v1/definitions') json = [definition];
		else if (path.startsWith('/api/v1/definitions/')) json = definition;
		else if (path.endsWith('/access')) json = { can_manage: true };
		else if (path.startsWith('/api/v1/lobby/')) json = lobby;
		await route.fulfill({ json });
	});
	let socket: WebSocketRoute | undefined;
	await page.routeWebSocket('**/api/v1/game/**', (ws) => {
		socket = ws;
	});
	await page.goto('/create?game=trivia');
	const start = page.getByRole('button', { name: 'Start Game' });
	await expect(start).toBeEnabled();
	await start.click();
	await expect(page).toHaveURL(/\/host\/ABCDE$/);
	await expect
		.poll(() => page.evaluate(() => document.fullscreenElement === document.documentElement))
		.toBe(true);
	await expect.poll(() => Boolean(socket)).toBe(true);
	await expect(page.locator('[data-cursor-idle]')).toHaveCount(0);
	let revision = 0;
	function patch(changes: object) {
		socket!.send(
			JSON.stringify({
				type_: 'runtime_patch',
				base_revision: revision,
				revision: ++revision,
				changes
			})
		);
	}
	patch({ lobby: { state: 'running' } });
	const stage = page.locator('.host-stage');
	await expect(stage).toBeVisible();
	await expect(stage).toHaveCSS('cursor', 'none');
	await expect(stage.locator('section').first()).toHaveCSS('cursor', 'none');
	await page.mouse.move(100, 100);
	await expect(stage).not.toHaveAttribute('data-cursor-idle');
	await expect(stage).toHaveAttribute('data-cursor-idle', '');
	await page.mouse.click(100, 100);
	await expect(stage).not.toHaveAttribute('data-cursor-idle');
	patch({ lobby: { state: 'paused' } });
	await expect(stage).toHaveCSS('cursor', 'none');
	patch({ lobby: { phase: 'finished' }, end_game: { revealed: false } });
	await expect(page.locator('.final-ready-panel')).toBeVisible();
	await expect(page.locator('.final-ready-panel')).toHaveCSS('cursor', 'none');
	patch({ lobby: { state: 'waiting_for_players' } });
	await expect(stage).toHaveCount(0);
	await expect(page.locator('[data-cursor-idle]')).toHaveCount(0);
	// Headless Chromium does not perform the native Escape fullscreen exit.
	// Verify Escape is not intercepted, then exercise the real fullscreenchange lifecycle.
	const escapeHandled = await page.evaluate(() => {
		const event = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true });
		document.dispatchEvent(event);
		return event.defaultPrevented;
	});
	expect(escapeHandled).toBe(false);
	await page.evaluate(() => document.exitFullscreen());
	await expect.poll(() => page.evaluate(() => document.fullscreenElement === null)).toBe(true);
	await page.goBack();
	await expect(start).toBeEnabled();
	await start.click();
	await expect(page).toHaveURL(/\/host\/ABCDE$/);
	await expect.poll(() => page.evaluate(() => document.fullscreenElement !== null)).toBe(true);
	await page.goBack();
	await expect(start).toBeVisible();
	await expect.poll(() => page.evaluate(() => document.fullscreenElement === null)).toBe(true);
	expect(errors).toEqual([]);
});
