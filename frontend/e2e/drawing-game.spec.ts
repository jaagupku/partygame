import { test, expect, type Page, type Browser, type BrowserContext } from '@playwright/test';

test.use({ actionTimeout: 10_000 });

async function room(browser: Browser, display: Page, count: number) {
	await display.addInitScript(() => localStorage.setItem('partygame-locale', JSON.stringify('en')));
	await display.goto('/create?game=drawing_mashup');
	const created = display.waitForResponse((r) => r.url().endsWith('/api/v1/lobby/create'));
	await display.getByRole('button', { name: 'Start Game', exact: true }).click();
	const lobby = await (await created).json();
	const contexts: BrowserContext[] = [];
	const pages: Page[] = [];
	const ids: string[] = [];
	const snapshots: Record<string, unknown>[][] = [];
	for (let i = 0; i < count; i++) {
		const context = await browser.newContext({
			baseURL: new URL(display.url()).origin,
			viewport: { width: 390, height: 844 }
		});
		contexts.push(context);
		await context.addInitScript(() =>
			localStorage.setItem('partygame-locale', JSON.stringify('en'))
		);
		const joined = await context.request.post('/api/v1/lobby/join', {
			data: { join_code: lobby.join_code, player_name: `Artist ${i}` }
		});
		expect(joined.ok()).toBeTruthy();
		const { player } = await joined.json();
		ids.push(player.id);
		const page = await context.newPage();
		await page.goto('/api/health');
		await page.evaluate((p) => localStorage.setItem('playerData', JSON.stringify(p)), player);
		const frames: Record<string, unknown>[] = [];
		snapshots.push(frames);
		page.on('websocket', (ws) =>
			ws.on('framereceived', (frame) => {
				try {
					const msg = JSON.parse(String(frame.payload));
					if (msg.type_ === 'runtime_snapshot') frames.push(msg);
				} catch {
					/* Non-JSON messages are not runtime frames. */
				}
			})
		);
		await page.goto(`/play/${lobby.join_code}`);
		pages.push(page);
	}
	await expect
		.poll(() => {
			const latest = snapshots[0].at(-1) as { players?: { status: string }[] } | undefined;
			return latest?.players?.filter((player) => player.status === 'connected').length ?? 0;
		})
		.toBe(count);
	await pages[0].getByRole('button', { name: 'Start Game', exact: true }).click();
	await expect(pages[0].getByLabel('Drawing topic', { exact: true })).toBeVisible();
	return { lobby, contexts, pages, ids, snapshots };
}

async function finishPhase(page: Page) {
	const phase = await page.locator('[data-drawing-phase]').getAttribute('data-drawing-phase');
	await page.getByRole('button', { name: 'Organizer controls', exact: true }).click();
	await page.getByRole('button', { name: 'End this phase', exact: true }).click();
	await page
		.getByRole('button', { name: 'End this phase now? Saved work will be submitted.', exact: true })
		.click();
	await expect
		.poll(() =>
			page
				.locator('[data-drawing-phase]')
				.evaluateAll((nodes) => nodes[0]?.getAttribute('data-drawing-phase') ?? null)
		)
		.not.toBe(phase);
}

async function draw(page: Page) {
	const canvas = page.locator('canvas.drawing-input-canvas');
	const box = await canvas.boundingBox();
	expect(box).not.toBeNull();
	await page.mouse.move(box!.x + 35, box!.y + 35);
	await page.mouse.down();
	await page.mouse.move(box!.x + 120, box!.y + 100, { steps: 12 });
	await page.mouse.up();
	await expect(page.getByRole('status', { name: '' }).filter({ hasText: 'Saved' })).toBeVisible();
}

for (const count of [3, 5]) {
	test(`${count} players: private queues, voting, gallery, and rematch`, async ({
		browser,
		page
	}, info) => {
		test.setTimeout(180_000);
		const game = await room(browser, page, count);
		try {
			for (let i = 0; i < count; i++) {
				await game.pages[i].getByLabel('Drawing topic', { exact: true }).fill(`A broad topic ${i}`);
				await game.pages[i]
					.getByLabel('Voting criterion', { exact: true })
					.fill(`Surprise criterion ${i}`);
				await game.pages[i].getByRole('button', { name: 'Done', exact: true }).click();
			}
			const drawings = count < 5 ? 2 : 3;
			for (let i = 0; i < count; i++) {
				const phone = game.pages[i];
				await expect(phone.getByText('Time to draw', { exact: true })).toBeVisible();
				const snapshot = game.snapshots[i].at(-1) as unknown as {
					drawing_game: { assignments: { topic: { text: string }; criterion: null }[] };
					drawing_private: object;
				};
				expect(snapshot.drawing_private).toEqual({});
				expect(snapshot.drawing_game.assignments).toHaveLength(drawings);
				expect(
					snapshot.drawing_game.assignments.every(
						(a) => a.topic.text !== `A broad topic ${i}` && a.criterion === null
					)
				).toBeTruthy();
				for (let d = 0; d < drawings; d++) {
					await phone
						.getByRole('navigation', { name: 'Your drawings' })
						.getByRole('button')
						.nth(d)
						.click();
					await draw(phone);
				}
				if (i === 0) {
					await phone.reload();
					await expect(
						phone.getByRole('navigation', { name: 'Your drawings' }).getByRole('button').first()
					).toContainText('✓');
					await expect(phone.getByRole('button', { name: 'Done', exact: true })).toBeEnabled();
				}
				await phone.getByRole('button', { name: 'Done', exact: true }).click();
			}
			for (let topic = 0; topic < count; topic++) {
				const voters = [];
				for (const phone of game.pages) {
					const blocked = phone.getByText("You can't vote right now", { exact: true });
					await expect(
						phone.getByText('Vote on the surprise criterion', { exact: true }).or(blocked)
					).toBeVisible();
					if (await blocked.isVisible()) {
						await expect(phone.locator('button.drawing-choice')).toHaveCount(0);
						await expect(phone.getByRole('button', { name: 'Done', exact: true })).toHaveCount(0);
					} else voters.push(phone);
				}
				for (const [index, phone] of voters.entries()) {
					await phone
						.locator('button.drawing-choice:not(:disabled)')
						.nth(index % drawings)
						.click();
					for (const label of ['Commend the topic (+10)', 'Commend the criterion (+10)']) {
						const input = phone.getByLabel(label, { exact: true });
						if (await input.isEnabled()) await input.check();
					}
					await phone.getByRole('button', { name: 'Done', exact: true }).click();
				}
				await expect(page.getByText('Topic results', { exact: true })).toBeVisible();
				if (topic === 0) {
					const reveal = page.locator('[data-reveal-stage]');
					await game.pages[0]
						.getByRole('button', { name: 'Organizer controls', exact: true })
						.click();
					await expect(reveal).toHaveAttribute('data-reveal-stage', 'revealPoints');
					await game.pages[0].getByRole('button', { name: 'Pause', exact: true }).click();
					await expect(reveal.getByText('Game paused', { exact: true })).toBeVisible();
					const frozen = await page.locator('[data-award]').allTextContents();
					await game.pages[1].reload();
					await expect(game.pages[1].locator('[data-reveal-stage]')).toHaveAttribute(
						'data-reveal-stage',
						'revealPoints'
					);
					expect(await page.locator('[data-award]').allTextContents()).toEqual(frozen);
					await game.pages[0].getByRole('button', { name: 'Resume', exact: true }).click();
					await game.pages[0].getByRole('button', { name: 'Close', exact: true }).click();
					await expect(reveal).toHaveAttribute('data-reveal-stage', 'revealSummary');
					await expect(game.pages[1].locator('[data-reveal-stage]')).toHaveAttribute(
						'data-reveal-stage',
						'revealSummary'
					);
					const result = (game.snapshots[0].at(-1) as unknown as { drawing_game: DrawingGameView })
						.drawing_game;
					for (const vote of result.matchup!.revealed_votes!) {
						for (const screen of [page, game.pages[1]]) {
							await expect(
								screen.locator(
									`[data-artwork-id="${vote.drawing_id}"] [data-voter-id="${vote.voter_id}"]`
								)
							).toContainText(vote.voter_name);
						}
					}
					for (const artwork of result.matchup!.drawings) {
						await expect(page.locator(`[data-award="${artwork.id}"]`)).toContainText(
							`+${artwork.points}`
						);
					}
					expect(result.matchup!.drawings.reduce((sum, art) => sum + art.points, 0)).toBe(1000);
					expect(
						await game.pages[1].evaluate(
							() => document.documentElement.scrollWidth <= window.innerWidth
						)
					).toBe(true);
					await page.screenshot({ path: info.outputPath('voting-results.png') });
					await game.pages[0].screenshot({
						path: info.outputPath('controller-results.png'),
						fullPage: true
					});
				}
				if (topic === 0 && count === 3) {
					// Let the real server deadline advance the game after the final summary.
					await expect(page.locator('[data-reveal-stage]')).toHaveCount(0);
				} else await finishPhase(game.pages[0]);
			}
			const gallery = page.getByRole('complementary', { name: 'Drawing gallery' });
			await expect(gallery).toBeVisible({ timeout: 35_000 });
			await expect(gallery.locator('canvas')).toBeVisible();
			const scoreboardBox = await page
				.getByRole('heading', { name: 'Full final scoreboard', exact: true })
				.boundingBox();
			const galleryBox = await gallery.boundingBox();
			expect(scoreboardBox!.y).toBeGreaterThanOrEqual(0);
			expect(galleryBox!.x).toBeGreaterThan(scoreboardBox!.x);
			expect(galleryBox!.y + galleryBox!.height).toBeLessThanOrEqual(1256);

			await expect(gallery.getByRole('heading').first()).toContainText(`1/${count * drawings}`);
			await expect(gallery.getByRole('heading').first()).toContainText(`2/${count * drawings}`, {
				timeout: 10_000
			});
			await gallery.getByRole('button', { name: 'Pause', exact: true }).click();
			await page.screenshot({ path: info.outputPath('gallery.png') });
			await page.evaluate(async () => {
				if (document.fullscreenElement) await document.exitFullscreen();
			});
			await page.setViewportSize({ width: 390, height: 844 });
			const narrowGallery = await gallery.boundingBox();
			const narrowStandings = await page
				.getByRole('heading', { name: 'Full final scoreboard', exact: true })
				.boundingBox();
			expect(narrowGallery!.y).toBeGreaterThan(narrowStandings!.y);
			expect(narrowGallery!.x + narrowGallery!.width).toBeLessThanOrEqual(390);
			await expect
				.poll(async () => (await gallery.locator('canvas').boundingBox())?.height ?? 0)
				.toBeGreaterThan(150);
			await gallery.locator('canvas').scrollIntoViewIfNeeded();
			await page.screenshot({ path: info.outputPath('gallery-mobile.png'), fullPage: true });
			await game.pages[0].getByRole('button', { name: 'Play again', exact: true }).click();
			await expect(game.pages[0].getByLabel('Writing time (seconds)')).toHaveValue('90');
			const continued = game.pages[0].waitForResponse((r) => r.url().endsWith('/continue'));
			await game.pages[0].getByRole('button', { name: 'Prepare next game', exact: true }).click();
			expect((await continued).ok()).toBeTruthy();
			await expect(
				game.pages[0].getByRole('button', { name: 'Start Game', exact: true })
			).toBeEnabled();
		} finally {
			await Promise.all(game.contexts.map((c) => c.close()));
		}
	});
}

test('missing drawings retain work and award the lone artist 1000 points', async ({
	browser,
	page
}) => {
	test.setTimeout(90_000);
	const game = await room(browser, page, 3);
	try {
		await finishPhase(game.pages[0]);
		for (const phone of game.pages)
			await expect(phone.getByText('Time to draw', { exact: true })).toBeVisible();
		const phone = game.pages[0];
		// Save both assignments but deliberately never mark this player done.
		await draw(phone);
		await phone
			.getByRole('navigation', { name: 'Your drawings' })
			.getByRole('button')
			.nth(1)
			.click();
		await draw(phone);
		await finishPhase(phone);
		for (let topic = 0; topic < 3; topic++) {
			if (
				await phone
					.getByText('Vote on the surprise criterion', { exact: true })
					.or(phone.getByText("You can't vote right now", { exact: true }))
					.count()
			)
				await finishPhase(phone);
			await expect(page.getByText('Topic results', { exact: true })).toBeVisible();
			await finishPhase(phone);
		}
		await expect(phone.getByText('2000', { exact: true }).first()).toBeVisible({ timeout: 10_000 });
	} finally {
		await Promise.all(game.contexts.map((c) => c.close()));
	}
});

test('main writing countdown is centered, animated, and respects reduced motion', async ({
	browser,
	page
}) => {
	const game = await room(browser, page, 3);
	try {
		const timer = page.locator('.prompt-countdown');
		await expect(timer).toBeVisible();
		await expect(game.pages[0].locator('.prompt-countdown')).toHaveCount(0);
		await page.evaluate(async () => {
			if (document.fullscreenElement) await document.exitFullscreen();
		});
		for (const viewport of [
			{ width: 1920, height: 1080 },
			{ width: 768, height: 600 },
			{ width: 390, height: 844 }
		]) {
			await page.setViewportSize(viewport);
			const stage = await page.locator('.writing-display').boundingBox();
			const box = await timer.boundingBox();
			expect(stage).not.toBeNull();
			expect(box).not.toBeNull();
			expect(Math.abs(box!.x + box!.width / 2 - stage!.x - stage!.width / 2)).toBeLessThan(3);
			expect(Math.abs(box!.y + box!.height / 2 - stage!.y - stage!.height / 2)).toBeLessThan(3);
			await expect(page.locator('.writing-status')).toBeInViewport();
		}
		await page.setViewportSize({ width: 1920, height: 1080 });
		await expect.poll(() => page.locator('.flip-in').count()).toBeGreaterThan(0);
		await expect.poll(() => page.locator('.digits.pulse').count(), { timeout: 12_000 }).toBe(1);
		await page.emulateMedia({ reducedMotion: 'reduce' });
		expect(
			await page.locator('.digits').evaluate((node) => getComputedStyle(node).animationName)
		).toBe('none');
		expect(
			await page
				.locator('.flip-in')
				.first()
				.evaluate((node) => getComputedStyle(node).animationName)
		).toBe('none');
		await page.screenshot({ path: '/tmp/drawing-prompt-countdown.png' });
		await finishPhase(game.pages[0]);
		await expect(timer).toHaveCount(0);
	} finally {
		await Promise.all(game.contexts.map((context) => context.close()));
	}
});
