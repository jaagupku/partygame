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
	revealSeconds = '4',
	extraNames: string[] = [],
	dropStartup = false
) {
	if (dropStartup) await dropStartupUpdates(page.context());
	await page.addInitScript(() => localStorage.setItem('partygame-locale', JSON.stringify('en')));
	await page.goto('/create?game=price_guessing');
	await page.getByLabel('Question mode').selectOption(mode);
	await page.getByLabel('Questions').selectOption('5');
	await page.getByLabel('Answer time').selectOption(seconds);
	await page.getByLabel('Progression').selectOption(String(hosted));
	if (!hosted) await page.getByLabel('Correct price reveal time').selectOption(revealSeconds);
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
	if (dropStartup) await dropStartupUpdates(context);
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
	const extraPhones: Page[] = [];
	for (const name of extraNames) {
		const extraContext = await browser.newContext({
			baseURL: new URL(page.url()).origin,
			viewport
		});
		contexts.push(extraContext);
		await extraContext.addInitScript(() =>
			localStorage.setItem('partygame-locale', JSON.stringify('en'))
		);
		const extra = await join(extraContext, lobby.join_code, name);
		await extra.goto(`/play/${lobby.join_code}`);
		extraPhones.push(extra);
	}
	await (host ?? phone).getByRole('button', { name: 'Start Game', exact: true }).click();
	await expect(phone.locator(imageSelector)).not.toHaveCount(0, { timeout: 20_000 });
	return { phone, host, contexts, frames, extraPhones };
}

async function answer(phone: Page, locale = 'en') {
	const input = phone.locator('input[inputmode="decimal"]');
	if (await input.count()) {
		await input.fill('2,50');
		await phone
			.getByRole('button', { name: locale === 'en' ? 'Submit price' : 'Saada hind', exact: true })
			.click();
	} else {
		const option = phone
			.locator('button')
			.filter({ has: phone.locator(imageSelector) })
			.first();
		await expect(option).toBeEnabled();
		await option.focus();
		await phone.keyboard.press('Enter');
	}
}

for (const viewport of [
	{ width: 360, height: 640 },
	{ width: 390, height: 844 }
]) {
	test(`mobile comparison lower option stays reachable at ${viewport.width}x${viewport.height}`, async ({
		browser,
		page
	}, testInfo) => {
		const { phone, contexts } = await start(browser, page, 'compare', true, 'en', '60', viewport);
		try {
			const options = phone.locator('.controller-player-input button[aria-pressed]');
			await expect(options).toHaveCount(2);
			if (viewport.width === 390) {
				// Stress the rendered cards with wrapping titles and the real image-error fallback.
				await options.evaluateAll((buttons) => {
					for (const button of buttons) {
						button.querySelector('p')!.textContent =
							'Extra long product title with additional model details and package information';
						button.querySelector('img')!.dispatchEvent(new Event('error'));
					}
				});
				await expect(phone.getByText('Product image unavailable', { exact: true })).toHaveCount(2);
			}
			const session = await phone.context().newCDPSession(phone);
			for (let swipe = 0; swipe < 4; swipe++) {
				const x = viewport.width / 2;
				await session.send('Input.dispatchTouchEvent', {
					type: 'touchStart',
					touchPoints: [{ x, y: viewport.height * 0.8 }]
				});
				for (let move = 1; move <= 10; move++) {
					await session.send('Input.dispatchTouchEvent', {
						type: 'touchMove',
						touchPoints: [{ x, y: viewport.height * (0.8 - move * 0.06) }]
					});
					await phone.waitForTimeout(20);
				}
				await session.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
			}
			await phone.waitForTimeout(300);

			const lowerOption = options.last();
			const assertReachable = async () => {
				const card = await lowerOption.boundingBox();
				const dock = await phone.locator('.reaction-buttons').boundingBox();
				expect(card).not.toBeNull();
				expect(dock).not.toBeNull();
				expect(card!.y + card!.height).toBeLessThanOrEqual(dock!.y - 4);
			};
			await assertReachable();
			const scrollY = await phone.evaluate(() => window.scrollY);
			// Let touch momentum settle and routine websocket updates arrive.
			await phone.waitForTimeout(1500);
			expect(await phone.evaluate(() => window.scrollY)).toBeCloseTo(scrollY, 0);
			await assertReachable();
			await phone.screenshot({ path: testInfo.outputPath('mobile-comparison.png') });
			const card = (await lowerOption.boundingBox())!;
			await phone.touchscreen.tap(card.x + card.width / 2, card.y + card.height - 8);
			await expect(lowerOption).toHaveAttribute('aria-pressed', 'true');
			await expect(phone.getByText('Answers and points', { exact: true })).toBeVisible();
			expect(await phone.evaluate(() => document.documentElement.scrollWidth)).toBe(viewport.width);
		} finally {
			for (const context of contexts) await context.close();
		}
	});
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
				expect(JSON.stringify(frames)).not.toContain('price_minor');
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
					await phone.locator('input[inputmode="decimal"]').fill('1.001');
					await expect(
						phone.getByRole('button', { name: 'Submit price', exact: true })
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
						'More expensive'
					);
					await expect(choice.locator('.choice-option')).toHaveCount(2);
					await expect(choice.locator('.choice-wrong')).toHaveCount(1);
					await expect(phone.locator('.guess-reveal-correct')).toContainText('More expensive');
				}
				await page.screenshot({ path: testInfo.outputPath('reveal.png') });
				await phone.reload();
				await phone.getByText('Product details', { exact: true }).click();
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
		await phone.getByText('Toote andmed', { exact: true }).click();
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
	await page.route('**/api/v1/game-types/price_guessing/availability', async (route) => {
		attempts++;
		if (attempts === 1) await route.fulfill({ status: 503, body: '{}' });
		else await route.fulfill({ json: { ranges: [], combinations: [] } });
	});
	await page.goto('/create?game=price_guessing');
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
	} finally {
		for (const context of contexts) await context.close();
	}
});

test('automatic price reveal Ready toggles the countdown speed', async ({ browser, page }) => {
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

test('correct price leads a quick closest-first reveal on display and phone', async ({
	browser,
	page
}, info) => {
	const { phone, extraPhones, contexts } = await start(
		browser,
		page,
		'guess',
		true,
		'en',
		'60',
		{ width: 390, height: 844 },
		'4',
		['Middle', 'Closest']
	);
	try {
		for (const [index, device] of [phone, ...extraPhones].entries()) {
			await device.locator('input[inputmode="decimal"]').fill(String(index * 0.5));
			await device.getByRole('button', { name: 'Submit price', exact: true }).click();
		}
		for (const device of [page, phone]) {
			const receipt = device.locator('.price-receipt');
			await expect(receipt).toBeVisible();
			const rows = receipt.locator('.guess-result');
			await expect(rows.locator('.guess-result-player > p:first-child')).toHaveText([
				'Closest',
				'Middle',
				'Test player'
			]);
			await expect(receipt.getByRole('link')).toHaveCount(0);
			const price = receipt.locator('.guess-reveal-amount');
			const size = await price.evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
			expect(size).toBeGreaterThanOrEqual(52);
			const frames = await rows.evaluateAll((nodes) =>
				nodes.map((node) => {
					const animation = node.getAnimations()[0];
					animation.pause();
					// Rows wait for the price to count up (0.5 s hold + 1.2 s count), then stagger.
					animation.currentTime = 1850;
					const style = getComputedStyle(node);
					return { opacity: Number(style.opacity), delay: parseFloat(style.animationDelay) };
				})
			);
			expect(frames[0].opacity).toBeGreaterThan(0);
			expect(frames[2].opacity).toBe(0);
			expect(frames[0].delay).toBeLessThan(frames[1].delay);
			expect(frames[1].delay).toBeLessThan(frames[2].delay);
			await rows.evaluateAll((nodes) =>
				nodes.forEach((node) => node.getAnimations().forEach((animation) => animation.finish()))
			);
			await receipt.screenshot({
				path: info.outputPath(device === page ? 'price-first-display.png' : 'price-first-phone.png')
			});
		}
		await phone.emulateMedia({ reducedMotion: 'reduce' });
		await expect(phone.locator('.guess-result').first()).toHaveCSS('animation-name', 'none');
		await expect(phone.locator('.guess-result').last()).toHaveCSS('opacity', '1');
		await phone.reload();
		await expect(phone.locator('.guess-result-player > p:first-child')).toHaveText([
			'Closest',
			'Middle',
			'Test player'
		]);
	} finally {
		for (const context of contexts) await context.close();
	}
});

for (const mode of ['guess', 'compare', 'mixed'] as const) {
	test(`${mode} aisle transition finishes before the answer timer opens`, async ({
		browser,
		page
	}, info) => {
		const errors: string[] = [];
		page.on('pageerror', (error) => errors.push(error.message));
		const { phone, host, contexts, frames } = await start(browser, page, mode, true);
		try {
			await answer(phone);
			await expect(page.locator('.price-receipt')).toBeVisible();
			// Record even the short-lived phase without relying on polling during its 600 ms window.
			for (const device of [page, phone])
				await device.evaluate(() => {
					const captures: {
						id: string;
						elapsed: string;
						outgoing: number;
						phone: boolean;
						disabled: boolean;
						transform: string;
					}[] = [];
					Object.assign(window, { aisleCaptures: captures });
					const observer = new MutationObserver(() => {
						const node = document.querySelector<HTMLElement>('[data-price-transition]');
						if (!node || captures.length > 100) return;
						captures.push({
							id: node.dataset.priceTransition!,
							elapsed: node.style.getPropertyValue('--travel-elapsed'),
							outgoing: node.querySelectorAll('.outgoing .product-card').length,
							phone: node.classList.contains('phone'),
							disabled: [
								...document.querySelectorAll<HTMLInputElement>(
									'.controller-player-input input, .controller-player-input button[aria-pressed]'
								)
							].every((input) => input.disabled),
							transform: getComputedStyle(node.querySelector('.incoming')!).transform
						});
					});
					observer.observe(document.body, { subtree: true, childList: true, attributes: true });
				});
			const nextQuestion = host!.getByRole('button', { name: /^Next question/ });
			if (mode === 'compare') {
				await nextQuestion.evaluate((button) => {
					(button as HTMLButtonElement).click();
					(button as HTMLButtonElement).click();
				});
			} else await nextQuestion.click();
			if (mode === 'guess')
				await page.screenshot({ path: info.outputPath('during-aisle.png'), animations: 'allow' });
			await expect
				.poll(() =>
					frames.some((frame) => {
						const step =
							frame.active_step ??
							(frame.changes as Record<string, unknown> | undefined)?.active_step;
						return (step as RuntimeStepState | undefined)?.price_transition != null;
					})
				)
				.toBe(true);
			await expect(
				phone
					.locator('.controller-player-input input, .controller-player-input button[aria-pressed]')
					.first()
			).toBeEnabled();
			const steps = frames
				.map(
					(frame) =>
						(frame.active_step ??
							(frame.changes as Record<string, unknown> | undefined)?.active_step) as
							RuntimeStepState | undefined
				)
				.filter((step): step is RuntimeStepState => !!step);
			const transition = steps.find((step) => step.price_transition)!;
			expect(transition.price_transition!.duration_ms).toBe(600);
			expect(transition.input_enabled).toBe(false);
			expect(transition.timer.ends_at).toBeNull();
			const opened = steps.find((step) => step.id === transition.id && step.input_enabled)!;
			expect(opened.timer.ends_at! - opened.timer.started_at!).toBeCloseTo(60, 3);
			for (const device of [page, phone]) {
				const captures = await device.evaluate(
					() =>
						(
							window as unknown as {
								aisleCaptures: {
									id: string;
									outgoing: number;
									phone: boolean;
									disabled: boolean;
									transform: string;
								}[];
							}
						).aisleCaptures
				);
				expect(captures.length).toBeGreaterThan(0);
				expect(new Set(captures.map((c) => c.id)).size).toBe(1);
				if (device === page) expect(captures.some((c) => c.outgoing > 0)).toBe(true);
				else {
					expect(
						captures.every(
							(c) => c.phone && c.disabled && c.outgoing === 0 && c.transform === 'none'
						)
					).toBe(true);
				}
				await expect(device.locator('[data-price-transition]')).toHaveCount(0);
				await expect(device.locator('.outgoing')).toHaveCount(0);
			}
			await page.screenshot({ path: info.outputPath('after-aisle.png') });
			await phone.screenshot({ path: info.outputPath('after-aisle-phone.png'), fullPage: true });
			await phone.reload();
			await expect(
				phone
					.locator('.controller-player-input input, .controller-player-input button[aria-pressed]')
					.first()
			).toBeEnabled();
			await expect(phone.locator('[data-price-transition]')).toHaveCount(0);
			if (mode === 'guess') {
				await answer(phone);
				await expect(page.locator('.price-receipt')).toBeVisible();
				await page.emulateMedia({ reducedMotion: 'reduce' });
				await host!.getByRole('button', { name: /^Next question/ }).click();
				await expect(page.locator('[data-price-transition]')).toHaveCount(1);
				await expect(page.locator('[data-price-transition] > .incoming')).toHaveCSS(
					'animation-name',
					'none'
				);
				await phone.reload();
				await expect(phone.locator('input[inputmode="decimal"]')).toBeEnabled();
				await expect(phone.locator('[data-price-transition]')).toHaveCount(0);
			}
			expect(errors).toEqual([]);
		} finally {
			for (const context of contexts) await context.close();
		}
	});
}

// Lose both notification and initial full-state deliveries, including the first
// recovery response. Every socket must recover without navigating or reconnecting.
async function dropStartupUpdates(context: BrowserContext) {
	await context.routeWebSocket('**/api/v1/game/**', (socket) => {
		const server = socket.connectToServer();
		let missed = 0;
		server.onMessage((message) => {
			const event = JSON.parse(String(message));
			if (event.type_ === 'start_game') return;
			if (event.type_ === 'runtime_snapshot' && event.lobby.state === 'running' && missed++ < 3)
				return;
			socket.send(message);
		});
	});
}

for (const hosted of [true, false]) {
	test(`start recovers missed updates without reload (${hosted ? 'hosted' : 'automatic'})`, async ({
		browser,
		page
	}) => {
		const { phone, host, contexts } = await start(
			browser,
			page,
			'guess',
			hosted,
			'en',
			'60',
			{ width: 390, height: 844 },
			'4',
			[],
			true
		);
		try {
			await expect(page.locator('.price-stage-products img')).toHaveCount(1, { timeout: 20_000 });
			await expect(phone.locator('input[inputmode="decimal"]')).toBeEnabled();
			if (host)
				await expect(host.getByRole('button', { name: 'Start Game', exact: true })).toHaveCount(0);
			await answer(phone);
			await expect(phone.getByText('Answers and points', { exact: true })).toBeVisible();
		} finally {
			for (const context of contexts) await context.close();
		}
	});
}
