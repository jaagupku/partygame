import { expect, test } from '@playwright/test';

for (const category of ['Furniture', 'Antiques & vintage', 'Clothing']) {
	test(`${category} mixes with electronics through reveal and reconnect`, async ({
		page,
		browser
	}, testInfo) => {
		await page.addInitScript(() => localStorage.setItem('partygame-locale', JSON.stringify('en')));
		await page.setViewportSize({ width: 390, height: 844 });
		await page.goto('/create?game=price_guessing');
		await expect(page.getByRole('checkbox', { name: category, exact: true })).toBeChecked();
		for (const name of ['Groceries', 'Furniture', 'Antiques & vintage', 'Clothing']) {
			if (name !== category) await page.getByRole('checkbox', { name, exact: true }).uncheck();
		}
		await page.getByLabel('Question mode').selectOption('compare');
		await page.getByRole('combobox', { name: 'Questions', exact: true }).selectOption('5');
		await page.getByLabel('Answer time').selectOption('60');
		await expect(page.getByRole('button', { name: 'Start Game', exact: true })).toBeEnabled();
		expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(
			false
		);
		await page.screenshot({ path: testInfo.outputPath('category-setup.png'), fullPage: true });
		const created = page.waitForResponse((r) => r.url().endsWith('/api/v1/lobby/create'));
		await page.getByRole('button', { name: 'Start Game', exact: true }).click();
		const lobby = await (await created).json();
		const context = await browser.newContext({
			baseURL: new URL(page.url()).origin,
			viewport: { width: 390, height: 844 }
		});
		try {
			const join = await context.request.post('/api/v1/lobby/join', {
				data: { join_code: lobby.join_code, player_name: 'Category player' }
			});
			const { player } = await join.json();
			await context.addInitScript((value) => {
				localStorage.setItem('playerData', JSON.stringify(value));
				localStorage.setItem('partygame-locale', JSON.stringify('en'));
			}, player);
			const phone = await context.newPage();
			const frames: string[] = [];
			phone.on('websocket', (socket) =>
				socket.on('framereceived', (frame) => frames.push(String(frame.payload)))
			);
			await phone.goto(`/play/${lobby.join_code}`);
			await phone.getByRole('button', { name: 'Start Game', exact: true }).click();
			const cards = phone.locator('.controller-player-input button[aria-pressed]');
			await expect(cards).toHaveCount(2);
			await phone.reload();
			await expect(cards).toHaveCount(2);
			expect(frames.join('')).not.toContain('price_minor');
			expect(frames.join('')).not.toContain('source_url');
			await expect(cards.filter({ hasText: 'E2E electronics' })).toHaveCount(1);
			await expect(
				cards.filter({
					hasText: `E2E ${category === 'Furniture' ? 'furniture' : category === 'Clothing' ? 'clothing' : 'antiques'}`
				})
			).toHaveCount(1);
			await cards.first().click();
			await expect(phone.getByText('Answers and points', { exact: true })).toBeVisible();
			await phone.getByText('Product details', { exact: true }).click();
			await expect(phone.getByRole('link', { name: 'View product' })).toHaveCount(2);
			await expect(
				phone.getByText(
					category === 'Furniture'
						? /Tootemaailm\s+·/
						: category === 'Clothing'
							? /Reserved\s+·/
							: /E-antiik\s+·/
				)
			).toBeVisible();
			await phone.screenshot({ path: testInfo.outputPath('category-reveal.png'), fullPage: true });
		} finally {
			await context.close();
		}
	});
}

test('Estonian category controls support keyboard selection and empty selection', async ({
	page
}) => {
	await page.addInitScript(() => localStorage.setItem('partygame-locale', JSON.stringify('et')));
	await page.goto('/create?game=price_guessing');
	for (const name of ['Toidukaubad', 'Elektroonika', 'Mööbel', 'Antiik ja vanavara', 'Riided']) {
		const checkbox = page.getByRole('checkbox', { name, exact: true });
		await expect(checkbox).toBeChecked();
		await checkbox.focus();
		await page.keyboard.press('Space');
	}
	await expect(page.getByRole('button', { name: 'Alusta uut mängu', exact: true })).toBeDisabled();
});
