import { expect, test, type Page, type WebSocketRoute } from '@playwright/test';

async function controller(page: Page, mode: 'guess' | 'compare' | 'drawing') {
	const players = Array.from({ length: 9 }, (_, i) => ({
		id: `p${i}`,
		game_id: 'answer-test',
		name: `Player ${i}`,
		status: 'connected',
		score: 0
	}));
	const lobby = {
		id: 'answer-test',
		run_id: 'run',
		join_code: 'ANSWER',
		host_enabled: true,
		host_id: 'host',
		state: 'running',
		phase: 'question_active',
		current_step: 0,
		players
	};
	const active_step = {
		id: 'step',
		title: 'Question',
		input_kind: mode === 'drawing' ? 'drawing' : mode === 'guess' ? 'number' : 'radio',
		input_enabled: true,
		input_options: ['a', 'b'],
		evaluation_type: mode === 'drawing' ? 'favorite_vote' : 'exact_text',
		evaluation_points: 100,
		timer: { seconds: 60, remaining_seconds: 60, started_at: 100, enforced: false },
		...(mode === 'drawing'
			? {}
			: {
					price_mode: mode,
					price_products: [
						{ id: 'a', title: 'First product', image_url: '/test-product.svg' },
						...(mode === 'compare'
							? [{ id: 'b', title: 'Second product', image_url: '/test-product.svg' }]
							: [])
					]
				})
	};
	let snapshot = {
		type_: 'runtime_snapshot',
		revision: 1,
		lobby,
		players,
		active_step,
		display_phase: mode === 'drawing' ? 'drawing_vote' : 'question_active',
		reviewing_history: false,
		can_review_previous: false,
		can_review_next: false,
		scoreboard_visible: false,
		buzzer_active: false,
		disabled_buzzer_player_ids: [],
		submitted_player_ids: mode === 'drawing' ? ['p0'] : [],
		submission_count: 0,
		pending_review_count: 0,
		drawing_items:
			mode === 'drawing'
				? players.slice(1).map((p, i) => ({
						id: p.id,
						label: `Drawing ${i + 1}`,
						value: { w: 512, h: 384, s: [] },
						vote_count: 0,
						points_awarded: 0
					}))
				: [],
		drawing_voted_player_ids: [] as string[],
		drawing_vote_count: 0,
		submissions: [],
		end_game: null
	};
	await page.addInitScript((player) => {
		localStorage.setItem('partygame-locale', JSON.stringify('en'));
		localStorage.setItem('playerData', JSON.stringify(player));
	}, players[0]);
	await page.route('**/api/v1/lobby/join-code/ANSWER', (route) => route.fulfill({ json: lobby }));
	await page.route('**/test-product.svg', (route) =>
		route.fulfill({
			contentType: 'image/svg+xml',
			body: '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80"><rect width="80" height="80" fill="skyblue"/></svg>'
		})
	);
	let socket: WebSocketRoute;
	const sent: Record<string, unknown>[] = [];
	const update = (changes: Record<string, unknown>) => {
		snapshot = { ...snapshot, ...changes, revision: snapshot.revision + 1 };
		socket.send(JSON.stringify(snapshot));
	};
	await page.routeWebSocket('**/api/v1/game/answer-test/controller/p0', (ws) => {
		socket = ws;
		ws.send(JSON.stringify(snapshot));
		ws.onMessage((message) => {
			const value = JSON.parse(String(message));
			sent.push(value);
			if (value.type_ === 'player_input_submitted') update({ submitted_player_ids: ['p0'] });
			if (value.type_ === 'drawing_vote_submitted') update({ drawing_voted_player_ids: ['p0'] });
		});
	});
	await page.goto('/play/ANSWER');
	await expect(page.locator('.controller-player-input')).toBeVisible();
	return { sent, update, event: (event: object) => socket.send(JSON.stringify(event)) };
}

test.use({ viewport: { width: 360, height: 640 }, isMobile: true, hasTouch: true });

test('price typing requires explicit submission and accepts a revised price', async ({ page }) => {
	const { sent, event, update } = await controller(page, 'guess');
	const input = page.locator('input[inputmode="decimal"]');
	await input.pressSequentially('12', { delay: 150 });
	event({ type_: 'collect_player_drafts', step_id: 'step', reason: 'timer_expired' });
	await input.pressSequentially(',50', { delay: 150 });
	expect(sent.filter((x) => x.type_ === 'player_input_submitted')).toEqual([]);
	await page.getByRole('button', { name: 'Submit price', exact: true }).click();
	await expect
		.poll(() => sent.filter((x) => x.type_ === 'player_input_submitted').map((x) => x.value))
		.toEqual(['12.50']);
	await input.fill('13,75');
	await page.getByRole('button', { name: 'Submit price', exact: true }).click();
	await expect
		.poll(() => sent.filter((x) => x.type_ === 'player_input_submitted').map((x) => x.value))
		.toEqual(['12.50', '13.75']);
	update({
		lobby: { id: 'answer-test', phase: 'step_complete', state: 'running', host_enabled: true }
	});
	await expect(input).toBeDisabled();
});

test('comparison selection can change after the server acknowledges the answer', async ({
	page
}) => {
	const { sent } = await controller(page, 'compare');
	const options = page.locator('.controller-player-input button[aria-pressed]');
	await options.first().tap();
	await expect.poll(() => sent.filter((x) => x.type_ === 'player_input_submitted').length).toBe(1);
	await expect(options.last()).toBeEnabled();
	await options.last().tap();
	await expect(options.last()).toHaveAttribute('aria-pressed', 'true');
	await expect
		.poll(() => sent.filter((x) => x.type_ === 'player_input_submitted').map((x) => x.value))
		.toEqual(['a', 'b']);
});

test('drawing cards scroll by touch without voting and allow changing a vote', async ({
	page
}, testInfo) => {
	const { sent } = await controller(page, 'drawing');
	const cards = page.locator('.drawing-vote-card');
	await expect(cards).toHaveCount(8);
	const first = (await cards.first().boundingBox())!;
	const second = (await cards.nth(1).boundingBox())!;
	expect(first.y).toBe(second.y);
	const session = await page.context().newCDPSession(page);
	await session.send('Input.dispatchTouchEvent', {
		type: 'touchStart',
		touchPoints: [{ x: 100, y: 500 }]
	});
	for (let y = 480; y >= 140; y -= 20) {
		await session.send('Input.dispatchTouchEvent', {
			type: 'touchMove',
			touchPoints: [{ x: 100, y }]
		});
		await page.waitForTimeout(20);
	}
	await session.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
	await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(50);
	expect(sent.filter((x) => x.type_ === 'drawing_vote_submitted')).toEqual([]);
	await cards.last().tap();
	await expect(cards.last()).toHaveAttribute('aria-pressed', 'true');
	await expect.poll(() => sent.filter((x) => x.type_ === 'drawing_vote_submitted').length).toBe(1);
	await cards.nth(6).tap();
	await expect(cards.nth(6)).toHaveAttribute('aria-pressed', 'true');
	await expect(cards.last()).toHaveAttribute('aria-pressed', 'false');
	await expect
		.poll(() => sent.filter((x) => x.type_ === 'drawing_vote_submitted').map((x) => x.drawing_id))
		.toEqual(['p8', 'p7']);
	expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(360);
	await page.screenshot({ path: testInfo.outputPath('drawing-voting.png') });
});
