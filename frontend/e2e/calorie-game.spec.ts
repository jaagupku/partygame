import { expect, test, type Browser, type BrowserContext, type Page } from '@playwright/test';

type Mode = 'guess' | 'compare' | 'mixed';
const imageSelector = 'img[src^="/api/v1/media/"]';

async function join(context: BrowserContext, code: string, name: string) {
	const response = await context.request.post('/api/v1/lobby/join', {
		data: { join_code: code, player_name: name }
	});
	expect(response.ok()).toBeTruthy();
	const { player } = await response.json();
	const page = await context.newPage();
	await page.goto('/api/health');
	await page.evaluate((value) => localStorage.setItem('playerData', JSON.stringify(value)), player);
	return page;
}

async function start(
	browser: Browser,
	page: Page,
	mode: Mode,
	hosted: boolean,
	locale = 'en',
	seconds = '60',
	viewport = { width: 390, height: 844 },
	revealSeconds = '4'
) {
	await page.addInitScript(() => localStorage.setItem('partygame-locale', JSON.stringify('en')));
	await page.goto('/create?game=calorie_guessing');
	await page.getByLabel('Question mode').selectOption(mode);
	await page.getByLabel('Questions').selectOption('5');
	await page.getByLabel('Answer time').selectOption(seconds);
	await page.getByLabel('Progression').selectOption(String(hosted));
	if (!hosted) await page.getByLabel('Correct calorie reveal time').selectOption(revealSeconds);
	const creation = page.waitForResponse((r) => r.url().endsWith('/api/v1/lobby/create'));
	await page.getByRole('button', { name: 'Start Game', exact: true }).click();
	const lobby = await (await creation).json();
	const contexts: BrowserContext[] = [];
	let host: Page | undefined;
	if (hosted) {
		host = await join(page.context(), lobby.join_code, 'Test host');
		await host.goto(`/play/${lobby.join_code}`);
	}
	const context = await browser.newContext({
		baseURL: new URL(page.url()).origin,
		viewport,
		isMobile: true,
		hasTouch: true
	});
	contexts.push(context);
	await context.addInitScript(
		(value) => localStorage.setItem('partygame-locale', JSON.stringify(value)),
		locale
	);
	const phone = await join(context, lobby.join_code, 'Test player');
	const frames: Record<string, unknown>[] = [];
	phone.on('websocket', (socket) =>
		socket.on('framereceived', (frame) => {
			try {
				frames.push(JSON.parse(String(frame.payload)));
			} catch {
				/* heartbeat */
			}
		})
	);
	await phone.goto(`/play/${lobby.join_code}`);
	await (host ?? phone).getByRole('button', { name: 'Start Game', exact: true }).click();
	await expect(phone.locator(imageSelector)).not.toHaveCount(0, { timeout: 20_000 });
	return { phone, host, contexts, frames };
}

async function answer(phone: Page, locale = 'en') {
	const input = phone.locator('input[inputmode="numeric"]');
	if (await input.count()) {
		await input.fill('250');
		await phone
			.getByRole('button', {
				name: locale === 'en' ? 'Submit guess' : 'Saada pakkumine',
				exact: true
			})
			.click();
	} else {
		const option = phone
			.locator('button')
			.filter({ has: phone.locator(imageSelector) })
			.first();
		await option.focus();
		await phone.keyboard.press('Enter');
	}
}

for (const mode of ['guess', 'compare', 'mixed'] as const) {
	for (const hosted of [false, true]) {
		test(`${mode}, ${hosted ? 'host-paced' : 'automatic'}: private question, keyboard answer, reveal, reconnect`, async ({
			browser,
			page
		}, testInfo) => {
			const { phone, host, contexts, frames } = await start(browser, page, mode, hosted);
			try {
				await phone.reload();
				await expect(phone.locator(imageSelector)).not.toHaveCount(0);
				expect(JSON.stringify(frames)).not.toContain('source_url');
				await expect(phone.getByText(/kcal per 100 (g|ml)/).first()).toBeVisible();
				expect(JSON.stringify(frames)).not.toContain('"kcal":');
				const displayTitles = await page
					.locator('.price-stage-products img')
					.evaluateAll((images) => images.map((img) => img.getAttribute('alt')));
				expect(
					await phone
						.locator(imageSelector)
						.evaluateAll((images) => images.map((img) => img.getAttribute('alt')))
				).toEqual(displayTitles);
				const boxes = await page.locator('.price-stage-products img').evaluateAll((images) =>
					images.map((img) => {
						const r = img.getBoundingClientRect();
						return {
							y: r.y,
							width: r.width,
							height: r.height,
							loaded: (img as HTMLImageElement).naturalWidth > 0
						};
					})
				);
				expect(boxes.length).toBeGreaterThan(0);
				for (const box of boxes) {
					expect(box.loaded).toBeTruthy();
					expect(box.height).toBeGreaterThan(400);
					expect(box.y).toBeGreaterThan(200);
				}
				if (boxes.length === 2) {
					expect(Math.abs(boxes[0].width - boxes[1].width)).toBeLessThan(1);
					expect(Math.abs(boxes[0].y - boxes[1].y)).toBeLessThan(1);
				}
				await page.screenshot({ path: testInfo.outputPath('display.png') });
				await phone.screenshot({ path: testInfo.outputPath('phone.png'), fullPage: true });
				if (mode === 'guess') {
					await phone.locator('input[inputmode="numeric"]').fill('1.001');
					await expect(
						phone.getByRole('button', { name: 'Submit guess', exact: true })
					).toBeDisabled();
				}
				// Reduced motion shows the final choice placement without travel.
				if (mode === 'compare' && hosted) await page.emulateMedia({ reducedMotion: 'reduce' });
				await answer(phone);
				await expect(phone.getByText('Answers and points', { exact: true })).toBeVisible();
				await expect(page.getByText('Answers and points', { exact: true })).toBeVisible();
				if (mode === 'compare') {
					// Avatars travel to their chosen product before the winner is marked.
					const choice = page.locator('.choice-reveal');
					await expect(choice).toBeVisible();
					await expect(choice.locator('.choice-player')).not.toHaveCount(0);
					if (hosted) {
						await expect(page.locator('.choice-reveal.choice-revealed')).toBeVisible({
							timeout: 1000
						});
					} else {
						await page.screenshot({ path: testInfo.outputPath('choice-moving.png') });
					}
					await expect(choice.locator('.choice-correct .choice-ribbon')).toHaveText(
						'More calories'
					);
					await expect(choice.locator('.choice-option')).toHaveCount(2);
					await expect(choice.locator('.choice-wrong')).toHaveCount(1);
					await expect(phone.locator('.guess-reveal-correct')).toContainText('More calories');
				}
				await page.screenshot({ path: testInfo.outputPath('reveal.png') });
				await page.evaluate(async () => {
					if (document.fullscreenElement) await document.exitFullscreen();
				});
				await page.setViewportSize({ width: 1280, height: 720 });
				const result = await page.locator('.calorie-reveal .guess-result').first().boundingBox();
				expect(result!.y + result!.height).toBeLessThan(720);
				await page.screenshot({ path: testInfo.outputPath('reveal-1280.png') });

				await phone.reload();
				await expect(phone.getByRole('link', { name: 'View product' })).not.toHaveCount(0);
				expect(await phone.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(
					false
				);
				if (host) {
					await expect(host.getByText('Manual score', { exact: true })).toHaveCount(0);
					await expect(
						host.getByRole('button', { name: 'Reset Question', exact: true })
					).toBeDisabled();
					await host.getByRole('button', { name: /^Next question/ }).click();
					await expect(phone.getByText('Answers and points', { exact: true })).toHaveCount(0);
				}
			} finally {
				for (const context of contexts) await context.close();
			}
		});
	}
}

test('Estonian phone instructions and reveal', async ({ browser, page }) => {
	const { phone, contexts } = await start(browser, page, 'mixed', true, 'et');
	try {
		await answer(phone, 'et');
		await expect(phone.getByText('Vastused ja punktid', { exact: true })).toBeVisible();
		await expect(phone.getByRole('link', { name: 'Vaata toodet' })).not.toHaveCount(0);
	} finally {
		for (const context of contexts) await context.close();
	}
});

test('empty content and request failures keep launch disabled and allow retry', async ({
	page
}) => {
	await page.addInitScript(() => localStorage.setItem('partygame-locale', JSON.stringify('en')));
	let attempts = 0;
	await page.route('**/api/v1/game-types/calorie_guessing/availability', async (route) => {
		attempts++;
		if (attempts === 1) await route.fulfill({ status: 503, body: '{}' });
		else await route.fulfill({ json: { ranges: [], combinations: [] } });
	});
	await page.goto('/create?game=calorie_guessing');
	await page.getByRole('button', { name: 'Try again', exact: true }).click();
	await expect(page.getByRole('button', { name: 'Start Game', exact: true })).toBeDisabled();
	expect(attempts).toBe(2);
});

test('automatic mixed game reaches finale, including a missing timed-out answer', async ({
	browser,
	page
}, testInfo) => {
	const { phone, contexts, frames } = await start(browser, page, 'mixed', false, 'en', '15');
	try {
		for (let question = 0; question < 5; question++) {
			await expect(phone.locator(imageSelector)).not.toHaveCount(0);
			if (question < 4) await answer(phone);
			await expect(phone.getByText('Answers and points', { exact: true })).toBeVisible({
				timeout: 20_000
			});
			if (question === 4) await expect(phone.getByText('No answer', { exact: true })).toBeVisible();
			if (question < 4) {
				await expect(phone.getByText('Answers and points', { exact: true })).toHaveCount(0, {
					timeout: 20_000
				});
			}
		}
		await expect.poll(() => JSON.stringify(frames).includes('"revealed":true')).toBe(true);
		await page.screenshot({ path: testInfo.outputPath('finale.png') });
		await phone.getByRole('button', { name: 'Play again', exact: true }).click();
		await expect(phone.getByRole('combobox', { name: 'Questions', exact: true })).toHaveValue('5');
		const continued = phone.waitForResponse((r) => r.url().endsWith('/continue'));
		await phone.getByRole('button', { name: 'Prepare next game', exact: true }).click();
		expect((await continued).ok()).toBeTruthy();
		await phone.reload();
		await phone.getByRole('button', { name: 'Start Game', exact: true }).click();
		await expect(phone.locator(imageSelector)).not.toHaveCount(0, { timeout: 20_000 });
		await answer(phone);
		await expect(phone.getByText('Answers and points', { exact: true })).toBeVisible();
	} finally {
		for (const context of contexts) await context.close();
	}
});

test('automatic calorie reveal Ready toggles the countdown speed', async ({ browser, page }) => {
	const { phone, contexts } = await start(
		browser,
		page,
		'guess',
		false,
		'en',
		'15',
		{ width: 390, height: 844 },
		'10'
	);
	try {
		await answer(phone);
		await expect(phone.getByText('Answers and points', { exact: true })).toBeVisible({
			timeout: 20_000
		});
		await expect(phone.locator('p').filter({ hasText: 'Time remaining' })).toContainText('1.00×');
		const ready = phone.getByRole('button', { name: 'Ready', exact: true });
		await ready.click();
		await expect(phone.getByRole('button', { name: 'Not ready', exact: true })).toHaveAttribute(
			'aria-pressed',
			'true'
		);
		await phone.reload();
		await expect(phone.getByRole('button', { name: 'Not ready', exact: true })).toBeVisible();
		await expect(phone.locator('p').filter({ hasText: 'Time remaining' })).toContainText('1.15×');
		await phone.getByRole('button', { name: 'Not ready', exact: true }).click();
		await expect(phone.getByRole('button', { name: 'Ready', exact: true })).toHaveAttribute(
			'aria-pressed',
			'false'
		);
		await expect(phone.locator('p').filter({ hasText: 'Time remaining' })).toContainText('1.00×');
		await expect(phone.getByText('Answers and points', { exact: true })).toHaveCount(0, {
			timeout: 20_000
		});
	} finally {
		for (const context of contexts) await context.close();
	}
});
