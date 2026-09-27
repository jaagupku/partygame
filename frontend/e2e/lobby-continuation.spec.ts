import { expect, test, type BrowserContext, type Page } from '@playwright/test';

async function join(context: BrowserContext, code: string, name: string) {
	const response = await context.request.post('/api/v1/lobby/join', {
		data: { join_code: code, player_name: name }
	});
	expect(response.ok()).toBeTruthy();
	const { player } = await response.json();
	const page = await context.newPage();
	await page.goto('/api/health');
	await page.evaluate((p) => localStorage.setItem('playerData', JSON.stringify(p)), player);
	await page.goto(`/play/${code}`);
	return page;
}

async function finishPriceGame(host: Page, players: Page[]) {
	for (let question = 0; question < 5; question++) {
		for (const phone of players) {
			await phone.locator('input[inputmode="decimal"]').fill('2.50');
			await phone.getByRole('button', { name: 'Submit price', exact: true }).click();
		}
		await expect(players[0].getByText('Answers and points', { exact: true })).toBeVisible();
		await host
			.getByRole('button', { name: question === 4 ? /^Final results/ : /^Next question/ })
			.click();
	}
	await expect(host.getByRole('button', { name: 'Play again', exact: true })).toBeVisible();
}

test('same lobby replays fresh content, preserves players, and switches game and host mode', async ({
	browser,
	page
}, testInfo) => {
	test.setTimeout(150_000);
	await page
		.context()
		.addInitScript(() => localStorage.setItem('partygame-locale', JSON.stringify('en')));
	const created = await page.request.post('/api/v1/lobby/create', {
		data: {
			game_type: 'price_guessing',
			host_enabled: true,
			price_settings: {
				mode: 'guess',
				product_ranges: ['groceries'],
				questions: 5,
				answer_seconds: 60,
				reveal_seconds: 4
			}
		}
	});
	expect(created.ok()).toBeTruthy();
	const lobby = await created.json();
	await page.goto(`/host/${lobby.join_code}`);
	const contexts: BrowserContext[] = [];
	try {
		for (let i = 0; i < 3; i++) {
			const context = await browser.newContext({
				baseURL: new URL(page.url()).origin,
				viewport: { width: 390, height: 844 }
			});
			await context.addInitScript(() =>
				localStorage.setItem('partygame-locale', JSON.stringify('en'))
			);
			contexts.push(context);
		}
		const host = await join(contexts[0], lobby.join_code, 'Replay host');
		const phones = [
			await join(contexts[1], lobby.join_code, 'Replay one'),
			await join(contexts[2], lobby.join_code, 'Replay two')
		];
		const original = await (await page.request.get(`/api/v1/lobby/${lobby.id}`)).json();
		await host.getByRole('button', { name: 'Start Game', exact: true }).click();
		await finishPriceGame(host, phones);
		await expect(phones[0].getByRole('button', { name: 'Play again', exact: true })).toHaveCount(0);
		expect((await phones[0].request.get(`/api/v1/lobby/${lobby.id}/setup`)).status()).toBe(403);
		const finished = await (await page.request.get(`/api/v1/lobby/${lobby.id}`)).json();
		await host.getByRole('button', { name: 'Play again', exact: true }).click();
		await expect(host.getByRole('combobox', { name: 'Questions', exact: true })).toHaveValue('5');
		await expect(host.getByLabel('Question mode')).toHaveValue('guess');
		await host.getByRole('button', { name: 'Back', exact: true }).click();
		expect((await (await page.request.get(`/api/v1/lobby/${lobby.id}`)).json()).run_id).toBe(
			finished.run_id
		);
		await expect(page.getByRole('region', { name: 'Keep playing', exact: true })).toHaveCount(0);
		expect((await page.request.get(`/api/v1/lobby/${lobby.id}/setup`)).status()).toBe(403);
		await host.getByRole('button', { name: 'Play again', exact: true }).click();
		await host.getByLabel('Answer time').selectOption('45');
		const replayResponse = host.waitForResponse((r) =>
			r.url().endsWith(`/lobby/${lobby.id}/continue`)
		);
		await host.getByRole('button', { name: 'Prepare next game', exact: true }).click();
		const replay = await (await replayResponse).json();
		expect(replay.run_id).not.toBe(finished.run_id);
		expect(replay.id).toBe(lobby.id);
		expect(replay.join_code).toBe(lobby.join_code);
		expect(replay.players.map((p: { id: string }) => p.id).sort()).toEqual(
			original.players.map((p: { id: string }) => p.id).sort()
		);
		expect(replay.players.every((p: { score: number }) => p.score === 0)).toBeTruthy();
		for (const phone of phones)
			await expect(phone.getByText('Waiting for game to start.', { exact: true })).toBeVisible();
		await phones[1].reload();
		await expect(phones[1].getByText('Waiting for game to start.', { exact: true })).toBeVisible();
		await host.getByRole('button', { name: 'Start Game', exact: true }).click();
		await finishPriceGame(host, phones);
		await host.getByRole('button', { name: 'Choose another game', exact: true }).click();
		await host.getByRole('combobox', { name: 'Choose a game', exact: true }).selectOption('trivia');
		await host.getByLabel('Host-enabled mode').uncheck();
		await host.screenshot({ path: testInfo.outputPath('next-game-mobile.png'), fullPage: true });
		await host.getByRole('button', { name: 'Prepare next game', exact: true }).click();
		await expect(page.getByRole('heading', { name: 'Demo Quiz', exact: true })).toBeVisible();
		await expect(host.getByRole('button', { name: 'Start Game', exact: true })).toBeVisible();
		const trivia = await (await page.request.get(`/api/v1/lobby/${lobby.id}`)).json();
		expect(trivia.game_type).toBe('trivia');
		expect(trivia.host_id).toBeNull();
		await host.getByRole('button', { name: 'Start Game', exact: true }).click();
		await expect
			.poll(async () => (await (await page.request.get(`/api/v1/lobby/${lobby.id}`)).json()).state)
			.toBe('running');
		await page.screenshot({ path: testInfo.outputPath('third-game-display.png') });
	} finally {
		for (const context of contexts) await context.close();
	}
});

test('automatic starter can replay unchanged settings and start again after reconnect', async ({
	browser,
	page
}) => {
	test.setTimeout(100_000);
	await page
		.context()
		.addInitScript(() => localStorage.setItem('partygame-locale', JSON.stringify('en')));
	const created = await page.request.post('/api/v1/lobby/create', {
		data: {
			game_type: 'price_guessing',
			host_enabled: false,
			price_settings: {
				mode: 'guess',
				product_ranges: ['groceries'],
				questions: 5,
				answer_seconds: 60,
				reveal_seconds: 4
			}
		}
	});
	expect(created.ok()).toBeTruthy();
	const lobby = await created.json();
	await page.goto(`/host/${lobby.join_code}`);
	const context = await browser.newContext({
		baseURL: new URL(page.url()).origin,
		viewport: { width: 390, height: 844 }
	});
	await context.addInitScript(() => localStorage.setItem('partygame-locale', JSON.stringify('en')));
	try {
		const starter = await join(context, lobby.join_code, 'Automatic starter');
		await starter.getByRole('button', { name: 'Start Game', exact: true }).click();
		for (let i = 0; i < 5; i++) {
			await starter.locator('input[inputmode="decimal"]').fill('2.50');
			await starter.getByRole('button', { name: 'Submit price', exact: true }).click();
			await expect(starter.getByText('Answers and points', { exact: true })).toBeVisible();
			await expect(starter.getByText('Answers and points', { exact: true })).toHaveCount(0);
		}
		await expect(page.getByRole('region', { name: 'Keep playing', exact: true })).toHaveCount(0);
		await starter.getByRole('button', { name: 'Play again', exact: true }).click();
		await expect(starter.getByRole('combobox', { name: 'Questions', exact: true })).toHaveValue(
			'5'
		);
		await expect(starter.getByRole('combobox', { name: 'Progression', exact: true })).toHaveValue(
			'false'
		);
		const prepared = starter.waitForResponse((r) =>
			r.url().endsWith(`/lobby/${lobby.id}/continue`)
		);
		await starter.getByRole('button', { name: 'Prepare next game', exact: true }).click();
		expect((await prepared).ok()).toBeTruthy();
		await starter.reload();
		await starter.getByRole('button', { name: 'Start Game', exact: true }).click();
		await expect(starter.locator('input[inputmode="decimal"]')).toHaveValue('');
		await starter.locator('input[inputmode="decimal"]').fill('2.50');
		await starter.getByRole('button', { name: 'Submit price', exact: true }).click();
		await expect(starter.getByText('Answers and points', { exact: true })).toBeVisible();
	} finally {
		await context.close();
	}
});
