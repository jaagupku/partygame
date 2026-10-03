import { expect, test, type Page } from '@playwright/test';

test.use({ actionTimeout: 10_000 });

type AudioProbe = { starts: { loop: boolean; duration: number }[]; contexts: AudioContext[] };
async function instrument(page: Page, locale = 'en') {
	await page.addInitScript((language) => {
		localStorage.setItem('partygame-locale', JSON.stringify(language));
		localStorage.setItem('partyGameColorMode', 'dark');
		const probe: AudioProbe = { starts: [], contexts: [] };
		Object.assign(window, { priceAudio: probe });
		const Native = window.AudioContext;
		window.AudioContext = class extends Native {
			constructor() {
				super();
				probe.contexts.push(this);
			}
			createBufferSource() {
				const source = super.createBufferSource();
				const start = source.start.bind(source);
				source.start = (...args: Parameters<typeof source.start>) => {
					probe.starts.push({ loop: source.loop, duration: source.buffer?.duration ?? 0 });
					start(...args);
				};
				return source;
			}
		};
	}, locale);
}
const audio = (page: Page) =>
	page.evaluate(() => {
		const p = (window as unknown as { priceAudio: AudioProbe }).priceAudio;
		return { starts: p.starts, states: p.contexts.map((c) => c.state) };
	});
async function appearance(page: Page, selector: string) {
	return page.locator(selector).evaluate((node) => {
		const s = getComputedStyle(node);
		return [
			s.backgroundColor,
			s.backgroundImage,
			s.color,
			s.borderColor,
			s.fontFamily,
			s.colorScheme
		];
	});
}
async function changeMode(page: Page, mode: string) {
	await page.evaluate(async (mode) => {
		const path = '/src/lib/theme.ts';
		(await import(/* @vite-ignore */ path)).appColorMode.set(mode);
	}, mode);
}

for (const language of ['en', 'et']) {
	test(`storefront and setup stay authored in ${language}, silent and isolated from quiz`, async ({
		page
	}, info) => {
		await instrument(page, language);
		await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' });
		await page.goto('/');
		const tile = page.locator('[data-presentation="price_guessing"]');
		await expect(tile.locator('img[src$="storefront.svg"]')).toBeVisible();
		const before = await appearance(page, '[data-presentation="price_guessing"]');
		for (const mode of ['light', 'system', 'dark']) {
			await changeMode(page, mode);
			await page.emulateMedia({ colorScheme: mode === 'dark' ? 'dark' : 'light' });
			expect(await appearance(page, '[data-presentation="price_guessing"]')).toEqual(before);
		}
		await expect(page.locator('body')).not.toHaveAttribute('data-presentation');
		await page.screenshot({ path: info.outputPath('selector.png'), fullPage: true });
		await tile.getByRole('link').click();
		await expect(page.locator('.store-department')).not.toHaveCount(0);
		await expect(page.locator('body')).toHaveAttribute('data-presentation', 'price_guessing');
		const setup = await appearance(page, '.store-setup .card');
		for (const mode of ['light', 'system', 'dark']) {
			await changeMode(page, mode);
			expect(await appearance(page, '.store-setup .card')).toEqual(setup);
		}
		expect((await audio(page)).starts).toHaveLength(0);
		await page.screenshot({ path: info.outputPath('setup.png'), fullPage: true });
		await page.setViewportSize({ width: 360, height: 740 });
		await page.screenshot({ path: info.outputPath('setup-phone.png'), fullPage: true });
		expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(360);
		await page.goto('/create?game=trivia');
		await expect(page.locator('body')).not.toHaveAttribute('data-presentation');
		expect(await page.evaluate(() => localStorage.getItem('partyGameColorMode'))).toBe('dark');
	});
}

test('bundled audio plays from Create; personal sounds default on; checkout keeps its fixed palette', async ({
	browser,
	page
}, info) => {
	await instrument(page);
	await page.goto('/create?game=price_guessing');
	await page.getByLabel('Question mode').selectOption('guess');
	await page.getByRole('combobox', { name: 'Questions', exact: true }).selectOption('5');
	await page.getByLabel('Progression').selectOption('true');
	const creation = page.waitForResponse((r) => r.url().endsWith('/lobby/create'));
	await page.getByRole('button', { name: 'Start Game', exact: true }).click();
	const lobby = await (await creation).json();
	await expect(page.locator('.store-welcome')).toBeVisible();
	await expect.poll(async () => (await audio(page)).starts.filter((s) => s.loop).length).toBe(1);
	expect((await audio(page)).starts.find((s) => s.loop)?.duration).toBe(40);
	await expect(page.locator('[data-presentation-audio]')).toBeVisible();
	await page.getByText('Sound', { exact: true }).click();
	await expect(page.getByLabel('Music', { exact: true })).toBeChecked();
	await expect(page.getByLabel('Sound effects', { exact: true })).toBeChecked();
	await page.getByLabel('Music', { exact: true }).uncheck();
	await page.getByLabel('Music', { exact: true }).check();
	await expect.poll(async () => (await audio(page)).starts.filter((s) => s.loop).length).toBe(2);
	await page.getByText('Sound', { exact: true }).click();
	await page.screenshot({ path: info.outputPath('lobby.png') });

	const host = await page.context().newPage();
	await host.addInitScript(() => localStorage.setItem('partygame-locale', JSON.stringify('en')));
	const phoneContext = await browser.newContext({
		baseURL: new URL(page.url()).origin,
		viewport: { width: 360, height: 740 }
	});
	const phone = await phoneContext.newPage();
	await instrument(phone, 'et');
	try {
		for (const [device, name] of [
			[host, 'Host'],
			[phone, 'Ostleja']
		] as const) {
			const response = await device.request.post('/api/v1/lobby/join', {
				data: { join_code: lobby.join_code, player_name: name }
			});
			const { player } = await response.json();
			await device.goto('/api/health');
			await device.evaluate((p) => localStorage.setItem('playerData', JSON.stringify(p)), player);
			await device.goto(`/play/${lobby.join_code}`);
		}
		await expect(phone.locator('[data-presentation-audio]')).toBeVisible();
		await host.getByRole('button', { name: 'Start Game', exact: true }).click();
		for (const device of [page, host, phone])
			await expect(device.locator('[data-presentation-audio]')).toHaveCount(0);
		await expect(phone.locator('input[inputmode="decimal"]')).toBeVisible();
		await phone.locator('input[inputmode="decimal"]').fill('2,50');
		expect((await audio(phone)).starts).toHaveLength(0);
		await phone.getByRole('button', { name: 'Saada hind', exact: true }).click();
		await expect(page.locator('.price-receipt')).toBeVisible();
		await expect
			.poll(async () => (await audio(page)).starts.some((s) => Math.abs(s.duration - 0.65) < 0.01))
			.toBe(true);
		await expect.poll(async () => (await audio(phone)).starts.length).toBe(1);
		expect((await audio(phone)).starts[0].loop).toBe(false);
		await page.emulateMedia({ reducedMotion: 'reduce' });
		await expect(page.locator('.price-checkout-label').first()).toHaveCSS('animation-name', 'none');
		const reveal = await appearance(page, '.price-checkout-label');
		for (const mode of ['light', 'system', 'dark']) {
			await changeMode(page, mode);
			await page.emulateMedia({ colorScheme: mode === 'dark' ? 'dark' : 'light' });
			expect(await appearance(page, '.price-checkout-label')).toEqual(reveal);
		}
		await page.screenshot({ path: info.outputPath('checkout.png') });
		await phone.screenshot({ path: info.outputPath('checkout-phone.png'), fullPage: true });
		for (let question = 1; question < 5; question++) {
			await host.getByRole('button', { name: /^Next question/ }).click();
			await expect(phone.locator('input[inputmode="decimal"]')).toBeVisible();
			await phone.locator('input[inputmode="decimal"]').fill('3,00');
			await phone.getByRole('button', { name: 'Saada hind', exact: true }).click();
			await expect(page.locator('.price-receipt')).toBeVisible();
		}
		await host.getByRole('button', { name: /^Final results/ }).click();
		await host.getByRole('button', { name: 'Reveal Finale', exact: true }).click();
		await expect(page.locator('.store-celebration')).toBeVisible();
		const disableAutoplay = host.getByRole('button', { name: 'Disable Autoplay', exact: true });
		if (await disableAutoplay.count()) await disableAutoplay.click();
		await host.getByRole('button', { name: 'Next Finale Stage', exact: true }).click();
		await host.getByRole('button', { name: 'Next Finale Stage', exact: true }).click();
		await expect(page.locator('.podium-card.place-1')).toBeVisible();
		await expect
			.poll(async () => (await audio(page)).starts.some((s) => s.duration === 2.8))
			.toBe(true);
		const podium = await appearance(page, '.podium-card.place-1');
		await changeMode(page, 'light');
		expect(await appearance(page, '.podium-card.place-1')).toEqual(podium);
		await page.screenshot({ path: info.outputPath('winner.png') });
		await phone.screenshot({ path: info.outputPath('final-receipt-phone.png'), fullPage: true });
		await host.getByRole('button', { name: 'Next Finale Stage', exact: true }).click();
		await host.getByRole('button', { name: 'Next Finale Stage', exact: true }).click();
		await expect(page.locator('.finale-shell .scoreboard-card .price-score-unit')).toBeVisible();
		await page.screenshot({ path: info.outputPath('standings.png') });
		// Decode every authored cue in a real browser, checking data and exact durations.
		const decoded = await page.evaluate(async () => {
			const context = new AudioContext();
			const names = ['bag', 'tick', 'register', 'scan', 'receipt', 'chime', 'confirm', 'victory'];
			const results = [];
			for (const name of names) {
				const response = await fetch(`/presentation/price/audio/${name}.wav`);
				const buffer = await context.decodeAudioData(await response.arrayBuffer());
				const data = buffer.getChannelData(0);
				results.push({
					name,
					duration: buffer.duration,
					peak: data.reduce((max, x) => Math.max(max, Math.abs(x)), 0)
				});
			}
			await context.close();
			return results;
		});
		expect(decoded).toHaveLength(8);
		for (const asset of decoded) {
			expect(asset.peak).toBeGreaterThan(0.05);
			expect(asset.peak).toBeLessThan(0.95);
		}
		await info.attach('decoded-audio.json', {
			body: JSON.stringify(decoded, null, 2),
			contentType: 'application/json'
		});
		await page.evaluate(() => {
			const link = document.createElement('a');
			link.href = '/';
			document.body.append(link);
			link.click();
		});
		await expect(page.locator('body')).not.toHaveAttribute('data-presentation');
		await expect
			.poll(async () => (await audio(page)).states.every((s) => s === 'closed'))
			.toBe(true);
	} finally {
		await host.close();
		await phoneContext.close();
	}
});
