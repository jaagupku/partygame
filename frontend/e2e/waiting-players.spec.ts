import { expect, test, type Page, type WebSocketRoute } from '@playwright/test';

async function display(page: Page, count = 3) {
	const players = Array.from({ length: count }, (_, i) => ({
		id: `p${i}`,
		name: `Player ${i}`,
		status: 'connected',
		score: 0,
		avatar_kind: i === 0 ? 'custom' : 'preset',
		avatar_preset_key: 'fox',
		avatar_url: i === 0 ? '/test-avatar.svg' : undefined
	}));
	const lobby = {
		id: 'waiting-test',
		run_id: 'run-1',
		join_code: 'WAIT',
		host_enabled: false,
		starter_id: 'p0',
		state: 'running',
		phase: 'question_active',
		current_step: 0,
		players
	};
	const step = {
		id: 'drawing',
		title: 'Draw something',
		input_kind: 'drawing',
		input_enabled: true,
		evaluation_type: 'favorite_vote',
		evaluation_points: 100,
		input_options: [],
		timer: { seconds: 60, remaining_seconds: 60, started_at: 100, enforced: false }
	};
	let snapshot = {
		type_: 'runtime_snapshot',
		revision: 1,
		lobby,
		players,
		active_step: step,
		display_phase: 'question_active',
		reviewing_history: false,
		can_review_previous: false,
		can_review_next: false,
		scoreboard_visible: false,
		buzzer_active: false,
		disabled_buzzer_player_ids: [],
		submitted_player_ids: [],
		price_ready_player_ids: [],
		price_reveal_remaining_seconds: null,
		submission_count: 0,
		pending_review_count: 0,
		drawing_items: [],
		drawing_voted_player_ids: [],
		drawing_vote_count: 0,
		submissions: [],
		end_game: null
	};
	await page.addInitScript(() => localStorage.setItem('partygame-locale', JSON.stringify('en')));
	await page.route('**/api/v1/lobby/join-code/WAIT', (route) => route.fulfill({ json: lobby }));
	await page.route('**/api/v1/lobby/waiting-test/access', (route) =>
		route.fulfill({ json: { can_manage: false } })
	);
	await page.route('**/test-avatar.svg', (route) =>
		route.fulfill({
			contentType: 'image/svg+xml',
			body: '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48"><rect width="48" height="48" fill="tomato"/></svg>'
		})
	);
	let socket: WebSocketRoute;
	await page.routeWebSocket('**/api/v1/game/waiting-test/host', (ws) => {
		socket = ws;
		ws.send(JSON.stringify(snapshot));
	});
	await page.goto('/host/WAIT');
	await expect(page.locator('.waiting-avatar')).toHaveCount(count);
	await expect
		.poll(() =>
			page
				.locator('.waiting-avatar')
				.first()
				.evaluate((el) => el.getAnimations().length)
		)
		.toBe(0);
	return {
		players,
		step,
		patch(changes: Record<string, unknown>) {
			const base = snapshot.revision;
			snapshot = { ...snapshot, ...changes, revision: base + 1 };
			socket.send(
				JSON.stringify({ type_: 'runtime_patch', base_revision: base, revision: base + 1, changes })
			);
		},
		snapshot(changes: Record<string, unknown>) {
			snapshot = { ...snapshot, ...changes, revision: snapshot.revision + 1 };
			socket.send(JSON.stringify(snapshot));
		},
		event(event: Record<string, unknown>) {
			socket.send(JSON.stringify(event));
		}
	};
}

test('answer, vote, reconnect and next-question animations keep stable slots', async ({ page }) => {
	const errors: string[] = [];
	page.on('pageerror', (error) => errors.push(error.message));
	const host = await display(page);
	const a = page.locator('.waiting-avatar[data-player-id="p0"]');
	const b = page.locator('.waiting-avatar[data-player-id="p1"]');
	const before = await b.boundingBox();
	await expect(a).toHaveAttribute('aria-label', 'Waiting for Player 0 to answer');
	await expect(a.locator('img')).toHaveAttribute('src', '/test-avatar.svg');
	host.patch({ submitted_player_ids: ['p0'], submission_count: 1 });
	await expect
		.poll(() => a.evaluate((el) => el.getAnimations().length).catch(() => 0))
		.toBeGreaterThan(0);
	await expect(a).toHaveCount(0);
	expect((await b.boundingBox())?.y).toBe(before?.y);
	host.event({ type_: 'player_disconnected', player_id: 'p1' });
	await expect(b).toHaveCount(0);
	host.event({ type_: 'player_connected', player_id: 'p1' });
	await expect(b).toHaveCount(1);
	host.patch({ submitted_player_ids: ['p0', 'p1', 'p2'], display_phase: 'drawing_vote' });
	await expect(page.locator('.waiting-avatar[aria-label$="to vote"]')).toHaveCount(3);
	host.patch({ drawing_voted_player_ids: ['p1'] });
	await expect(b).toHaveCount(0);
	// A resync restores the same pending voters without replaying entrances.
	await expect.poll(() => a.evaluate((el) => el.getAnimations().length)).toBe(0);
	host.snapshot({});
	await expect(a).toHaveCount(1);
	expect(await a.evaluate((el) => el.getAnimations().length)).toBe(0);
	host.patch({ display_phase: 'answer_reveal' });
	await expect(page.locator('.waiting-avatar')).toHaveCount(0);
	host.patch({
		active_step: { ...host.step, id: 'next', title: 'Next drawing' },
		display_phase: 'question_active',
		submitted_player_ids: [],
		submission_count: 0,
		drawing_voted_player_ids: []
	});
	await expect(page.locator('.waiting-avatar')).toHaveCount(3);
	await expect.poll(() => a.evaluate((el) => el.getAnimations().length)).toBe(0);
	const rail = await page.locator('.waiting-rail').boundingBox();
	const stage = await page.locator('.waiting-rail + section').evaluate((el) => ({
		left: el.getBoundingClientRect().left,
		padding: parseFloat(getComputedStyle(el).paddingLeft)
	}));
	expect(stage.left + stage.padding).toBeGreaterThanOrEqual(rail!.x + rail!.width);
	host.patch({ scoreboard_visible: true });
	await expect(page.locator('aside')).toHaveCSS('opacity', '1');
	await expect(a).toHaveCount(1);
	const scoreboard = await page.locator('aside').boundingBox();
	expect(scoreboard!.x).toBeGreaterThan(rail!.x + rail!.width);
	await page.screenshot({ path: '/tmp/waiting-desktop.png' });
	expect(errors).toEqual([]);
});

test('large narrow display wraps circles and respects reduced motion', async ({ page }) => {
	await page.setViewportSize({ width: 390, height: 844 });
	await page.emulateMedia({ reducedMotion: 'reduce' });
	const host = await display(page, 30);
	const avatars = page.locator('.waiting-avatar');
	const boxes = await avatars.evaluateAll((els) =>
		els.map((el) => {
			const r = el.getBoundingClientRect();
			return { x: r.x, y: r.y, right: r.right, bottom: r.bottom, width: r.width };
		})
	);
	expect(new Set(boxes.map((b) => b.x)).size).toBeGreaterThan(1);
	for (const box of boxes) {
		expect(box.width).toBe(32);
		expect(box.x).toBeGreaterThanOrEqual(0);
		expect(box.y).toBeGreaterThanOrEqual(0);
		expect(box.right).toBeLessThanOrEqual(390);
		expect(box.bottom).toBeLessThanOrEqual(844);
	}
	host.patch({ submitted_player_ids: ['p0'] });
	await expect(avatars).toHaveCount(29);
	expect(await avatars.first().evaluate((el) => el.getAnimations().length)).toBe(0);
	await page.screenshot({ path: '/tmp/waiting-narrow.png' });
});
