import { expect, test, type Page, type WebSocketRoute } from '@playwright/test';

// Profiles are injected into Vite's served module only. No fixture identity enters production.
async function fixture(page: Page, phone = false) {
	await page.addInitScript(() => {
		localStorage.setItem('partygame-locale', JSON.stringify('en'));
		localStorage.setItem('partyGameColorMode', 'light');
		localStorage.setItem(
			'playerData',
			JSON.stringify({ id: 'p1', name: 'Player', game_id: 'presentation' })
		);
		const contexts: AudioContext[] = [];
		const starts: boolean[] = [];
		Object.assign(window, { presentationContexts: contexts, presentationStarts: starts });
		const NativeContext = window.AudioContext;
		window.AudioContext = class extends NativeContext {
			constructor() {
				super();
				contexts.push(this);
			}
			createBufferSource() {
				const source = super.createBufferSource();
				const start = source.start.bind(source);
				source.start = (...args: Parameters<typeof source.start>) => {
					starts.push(source.loop);
					start(...args);
				};
				return source;
			}
		};
	});
	// One second of a quiet sine tone exercises real fetch/decode/playback in Chromium.
	const wav = Buffer.alloc(44 + 16000);
	wav.write('RIFF');
	wav.writeUInt32LE(wav.length - 8, 4);
	wav.write('WAVEfmt ', 8);
	wav.writeUInt32LE(16, 16);
	wav.writeUInt16LE(1, 20);
	wav.writeUInt16LE(1, 22);
	wav.writeUInt32LE(8000, 24);
	wav.writeUInt32LE(16000, 28);
	wav.writeUInt16LE(2, 32);
	wav.writeUInt16LE(16, 34);
	wav.write('data', 36);
	wav.writeUInt32LE(16000, 40);
	for (let i = 0; i < 8000; i++)
		wav.writeInt16LE(Math.round(300 * Math.sin((i * 2 * Math.PI * 220) / 8000)), 44 + i * 2);
	await page.route('**/fixture-audio.wav', (route) =>
		route.fulfill({ contentType: 'audio/wav', body: wav })
	);
	await page.route('**/src/lib/presentation/registry.ts*', async (route) => {
		const response = await route.fetch();
		await route.fulfill({
			response,
			body: `${(await response.text()).replace('registerPresentation(pricePresentation);', '')}\nregisterPresentation({gameType:'price_guessing',appearance:{palette:{primary:'#123456',background:'#eef2f6'}}, audio:{music:'/fixture-audio.wav',effects:{submissionReceived:{src:'/fixture-audio.wav'},answerReveal:{src:'/fixture-audio.wav'}}}, variants:{receipt:{appearance:{palette:{primary:'#654321'}},music:'/fixture-audio.wav'}},adapt:(state)=>({variant:state.displayPhase==='answer_reveal'?'receipt':'default'})});`
		});
	});
	const lobby = {
		id: 'presentation',
		run_id: 'r1',
		join_code: 'ABCDE',
		game_type: 'price_guessing',
		definition_title: 'Fixture',
		state: 'waiting_for_players',
		host_enabled: false,
		players: [{ id: 'p1', name: 'Player', score: 0, status: 'connected' }]
	};
	await page.route('**/api/**', async (route) => {
		const path = new URL(route.request().url()).pathname;
		let json: unknown = {};
		if (path === '/api/v1/auth/me') json = null;
		else if (path === '/api/v1/game-types')
			json = ['price_guessing', 'trivia', 'calorie_guessing'].map((id) => ({
				id,
				localization_key:
					id === 'price_guessing'
						? 'priceGuessing'
						: id === 'calorie_guessing'
							? 'calorieGuessing'
							: 'trivia',
				availability: 'available'
			}));
		else if (path.endsWith('/availability'))
			json = {
				ranges: [{ product_range: 'groceries', available: true }],
				combinations: [{ mode: 'mixed', product_ranges: ['groceries'], questions: 10 }]
			};
		else if (path.endsWith('/access')) json = { can_manage: true };
		else if (path.startsWith('/api/v1/lobby/')) json = lobby;
		await route.fulfill({ json });
	});
	let socket: WebSocketRoute | undefined;
	await page.routeWebSocket('**/api/v1/game/**', (ws) => {
		socket = ws;
	});
	let revision = 0;
	return {
		async open() {
			await page.goto(`/${phone ? 'play' : 'host'}/ABCDE`);
			await expect.poll(() => Boolean(socket)).toBe(true);
		},
		snapshot(changes: object) {
			socket!.send(
				JSON.stringify({
					type_: 'runtime_snapshot',
					revision: ++revision,
					lobby: { ...lobby, state: 'running' },
					players: lobby.players,
					active_step: null,
					disabled_buzzer_player_ids: [],
					submitted_player_ids: [],
					drawing_items: [],
					submission_count: 0,
					pending_review_count: 0,
					display_phase: 'question_active',
					...changes
				})
			);
		},
		patch(changes: object) {
			socket!.send(
				JSON.stringify({
					type_: 'runtime_patch',
					base_revision: revision,
					revision: ++revision,
					changes
				})
			);
		}
	};
}

test('opt-in display activates real Web Audio, scopes variants and restores neutral navigation', async ({
	page
}, testInfo) => {
	const errors: string[] = [];
	page.on('pageerror', (error) => errors.push(error.message));
	const app = await fixture(page);
	await page.goto('/create?game=price_guessing');
	await expect(page.locator('body')).toHaveAttribute('data-presentation', 'price_guessing');
	await expect(page.locator('[data-presentation-audio]')).toHaveCount(0);
	await page.getByRole('button', { name: 'Start Game', exact: true }).click();
	await expect(page).toHaveURL(/\/host\/ABCDE$/);
	await expect.poll(() => page.evaluate(() => document.fullscreenElement !== null)).toBe(true);
	app.patch({ lobby: { state: 'waiting_for_players' } });
	await expect(page.locator('body')).toHaveCSS('--party-primary', '#123456');
	const sound = page.locator('[data-presentation-audio] summary');
	await sound.focus();
	await page.keyboard.press('Enter');
	await expect(page.getByLabel('Music volume', { exact: true })).toBeVisible();
	await expect
		.poll(() =>
			page.evaluate(() =>
				(window as unknown as { presentationContexts: AudioContext[] }).presentationContexts.some(
					(c) => c.state === 'running'
				)
			)
		)
		.toBe(true);
	await expect
		.poll(() =>
			page.evaluate(
				() =>
					(window as unknown as { presentationStarts: boolean[] }).presentationStarts.filter(
						Boolean
					).length
			)
		)
		.toBe(1);
	await page.screenshot({ path: testInfo.outputPath('display-audio.png') });
	await page.getByLabel('Music volume', { exact: true }).fill('40');
	await expect
		.poll(() =>
			page.evaluate(
				() =>
					JSON.parse(localStorage.getItem('partygame-presentation-audio-v1:host-display')!)
						.musicVolume
			)
		)
		.toBe(0.4);
	app.patch({ lobby: { state: 'running' } });
	await expect(page.locator('[data-presentation-audio]')).toHaveCount(0);
	app.snapshot({ display_phase: 'answer_reveal' });
	await expect
		.poll(() =>
			page.evaluate(
				() =>
					(window as unknown as { presentationStarts: boolean[] }).presentationStarts.filter(
						(loop) => !loop
					).length
			)
		)
		.toBe(1);
	await expect(page.locator('body')).toHaveCSS('--party-primary', '#654321');
	const authoredStyle = await page.locator('body').getAttribute('style');
	await page.evaluate(async () => {
		const path = '/src/lib/theme.ts';
		const theme = await import(/* @vite-ignore */ path);
		theme.appColorMode.set('dark');
	});
	await expect(page.locator('body')).toHaveAttribute('style', authoredStyle!);
	await expect(page.locator('body')).toHaveCSS('color-scheme', 'light');
	await page.emulateMedia({ colorScheme: 'dark' });
	await page.evaluate(async () => {
		const path = '/src/lib/theme.ts';
		const theme = await import(/* @vite-ignore */ path);
		theme.appColorMode.set('system');
	});
	await expect(page.locator('body')).toHaveCSS('--party-primary', '#654321');
	await page.emulateMedia({ colorScheme: 'light' });
	await expect(page.locator('body')).toHaveCSS('--party-primary', '#654321');
	await page.emulateMedia({ colorScheme: 'dark' });
	await expect(page.locator('body')).toHaveCSS('--party-primary', '#654321');
	await expect(page.locator('body')).toHaveAttribute('style', authoredStyle!);
	await page.evaluate(async () => {
		const path = '/src/lib/i18n.ts';
		const i18n = await import(/* @vite-ignore */ path);
		i18n.locale.set('et');
	});
	app.patch({ lobby: { state: 'waiting_for_players' } });
	await page.locator('[data-presentation-audio] summary').click();
	await expect(page.getByLabel('Muusika helitugevus')).toBeVisible();
	app.patch({ lobby: { game_type: 'trivia', run_id: 'quiz' } });
	await expect(page.locator('body')).not.toHaveAttribute('data-presentation');
	await expect(page.locator('[data-presentation-audio]')).toHaveCount(0);
	await expect
		.poll(() =>
			page.evaluate(() =>
				(window as unknown as { presentationContexts: AudioContext[] }).presentationContexts.every(
					(c) => c.state === 'closed'
				)
			)
		)
		.toBe(true);
	await page.goBack();
	await expect(page).toHaveURL(/\/create/);
	await expect.poll(() => page.evaluate(() => document.fullscreenElement === null)).toBe(true);
	expect(errors).toEqual([]);
});

test('narrow phones default personal effects on in the lobby, portal scope and keyboard controls', async ({
	page
}, testInfo) => {
	await page.setViewportSize({ width: 390, height: 844 });
	const app = await fixture(page, true);
	await app.open();
	const controls = page.locator('[data-presentation-audio]');
	await controls.locator('summary').focus();
	await page.keyboard.press('Enter');
	await expect(page.getByLabel('Personal confirmations')).toBeChecked();
	await expect(page.getByLabel('Music', { exact: true })).toHaveCount(0);
	await page.getByLabel('Personal confirmations').check();
	await expect(page.getByLabel('Effects volume')).toHaveValue('35');
	const box = await controls.boundingBox();
	expect(box!.x).toBeGreaterThanOrEqual(0);
	expect(box!.x + box!.width).toBeLessThanOrEqual(390);
	app.patch({ lobby: { state: 'running' } });
	await expect(controls).toHaveCount(0);
	await expect(page.locator('.reaction-dock')).toBeVisible();
	await expect(page.locator('.reaction-dock')).toHaveCSS('--party-primary', '#123456');
	app.patch({ display_phase: 'answer_reveal' });
	await expect(page.locator('.reaction-dock')).toHaveCSS('--party-primary', '#654321');
	await page.screenshot({ path: testInfo.outputPath('phone-audio.png') });
});

test('homepage cards isolate an enabled profile and stay silent', async ({ page }) => {
	await fixture(page);
	await page.goto('/');
	const price = page
		.locator('.card')
		.filter({ has: page.getByRole('heading', { name: 'Price Guessing', exact: true }) });
	const trivia = page
		.locator('.card')
		.filter({ has: page.getByRole('heading', { name: 'Trivia', exact: true }) });
	await expect(price).toHaveCSS('--party-primary', '#123456');
	await expect(trivia).toHaveCSS('--party-primary', '#0ea5e9');
	await expect(page.locator('body')).not.toHaveAttribute('data-presentation');
	await expect(page.locator('[data-presentation-audio]')).toHaveCount(0);
	expect(
		await page.evaluate(
			() =>
				(window as unknown as { presentationContexts: AudioContext[] }).presentationContexts.length
		)
	).toBe(0);
});
