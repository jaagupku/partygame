import { expect, type Page } from '@playwright/test';

/**
 * Window shapes the main display must look identical in: large and small 16:9, ultrawide
 * (bars left and right), and a window narrower and taller than every layout breakpoint.
 */
const WINDOWS = [
	{ width: 1920, height: 1080 },
	{ width: 1280, height: 720 },
	{ width: 2560, height: 1080 },
	{ width: 900, height: 1100 }
];

type StageLayout = {
	fit: number;
	aspect: number;
	rects: { selector: string; box: number[] }[];
	missing: string[];
};

/** Element boxes in stage design pixels, so the window size and letterboxing cancel out. */
function measure(page: Page, selectors: string[]): Promise<StageLayout | null> {
	return page.evaluate((list) => {
		const stage = document.querySelector<HTMLElement>('.game-stage');
		if (!stage) return null;
		const frame = stage.getBoundingClientRect();
		const scale = frame.width / stage.offsetWidth;
		const missing: string[] = [];
		const rects = list.flatMap((selector) => {
			const elements = [...stage.querySelectorAll(selector)];
			if (!elements.length) missing.push(selector);
			return elements.map((element) => {
				const rect = element.getBoundingClientRect();
				return {
					selector,
					box: [
						(rect.left - frame.left) / scale,
						(rect.top - frame.top) / scale,
						rect.width / scale,
						rect.height / scale
					]
				};
			});
		});
		return {
			// 1 when the stage touches the window on its limiting side.
			fit: Math.max(frame.width / window.innerWidth, frame.height / window.innerHeight),
			aspect: frame.width / frame.height,
			rects,
			missing
		};
	}, selectors);
}

/** Empty when the layouts agree within the tolerance (design pixels); otherwise names the first difference. */
function mismatch(reference: StageLayout, layout: StageLayout | null, tolerance = 0.5) {
	if (!layout) return 'no stage';
	if (Math.abs(layout.fit - 1) > 0.002) return `stage does not fill the window (fit ${layout.fit})`;
	if (layout.rects.length !== reference.rects.length)
		return `${layout.rects.length} elements instead of ${reference.rects.length}`;
	for (const [index, { selector, box }] of reference.rects.entries())
		for (const [side, name] of ['left', 'top', 'width', 'height'].entries()) {
			const actual = layout.rects[index].box[side];
			if (Math.abs(box[side] - actual) > tolerance)
				return `${selector} ${name}: ${actual.toFixed(2)} instead of ${box[side].toFixed(2)}`;
		}
	return '';
}

/** Smallest text size on the main display, in stage design pixels (it is watched on a TV). */
const MIN_TV_TEXT_PX = 22;

/**
 * The main display is read from across the room: no visible text inside the stage may be smaller
 * than MIN_TV_TEXT_PX, and nothing may scroll (a TV has no scrollbar to reach).
 */
export async function expectStageReadable(page: Page) {
	const problems = await page.evaluate((minimum) => {
		const stage = document.querySelector<HTMLElement>('.game-stage');
		if (!stage) return ['no stage'];
		const found = new Set<string>();
		const name = (element: Element) =>
			`${element.tagName.toLowerCase()}${[...element.classList]
				.filter((c) => !c.startsWith('svelte-'))
				.map((c) => `.${c}`)
				.join('')}`;
		const walker = document.createTreeWalker(stage, NodeFilter.SHOW_TEXT);
		while (walker.nextNode()) {
			const text = walker.currentNode.textContent?.trim();
			const element = walker.currentNode.parentElement;
			if (!text || !(element instanceof HTMLElement)) continue;
			// Hidden, transparent and screen-reader-only text is not part of the picture.
			if (!element.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
			const rect = element.getBoundingClientRect();
			if (rect.width <= 1 || rect.height <= 1) continue;
			const size = parseFloat(getComputedStyle(element).fontSize);
			if (size < minimum) found.add(`${name(element)} "${text.slice(0, 40)}" is ${size}px`);
		}
		for (const element of stage.querySelectorAll('*')) {
			const { overflowX, overflowY } = getComputedStyle(element);
			const scrollsY =
				/auto|scroll/.test(overflowY) && element.scrollHeight > element.clientHeight + 1;
			const scrollsX =
				/auto|scroll/.test(overflowX) && element.scrollWidth > element.clientWidth + 1;
			if (scrollsY || scrollsX) found.add(`${name(element)} scrolls`);
		}
		return [...found];
	}, MIN_TV_TEXT_PX);
	expect(problems, 'the main display reads from across the room without scrolling').toEqual([]);
}

/**
 * The fixed stage must show the same picture in every window: only its scale may change.
 * List elements that come to rest (no looping animation or ticking countdown).
 */
export async function expectStageInvariant(page: Page, selectors: string[]) {
	const original = page.viewportSize()!;
	// The display enters fullscreen on creation; a fullscreen window cannot be resized.
	await page.evaluate(async () => {
		if (document.fullscreenElement) await document.exitFullscreen();
	});
	try {
		await page.setViewportSize(WINDOWS[0]);
		// Take the reference once entrance animations have finished and the stage has rescaled.
		let latest = await measure(page, selectors);
		await expect
			.poll(async () => {
				const previous = latest;
				latest = await measure(page, selectors);
				// Stricter than the comparison below, so the tail of an easing curve does not pass as rest.
				return previous && latest ? mismatch(previous, latest, 0.01) : 'no stage';
			})
			.toBe('');
		const reference = latest;
		if (!reference) throw new Error('no stage');
		expect(reference.missing, 'every selector matches inside the stage').toEqual([]);
		expect(reference.aspect).toBeCloseTo(16 / 9, 2);
		for (const size of WINDOWS.slice(1)) {
			await page.setViewportSize(size);
			await expect
				.poll(async () => mismatch(reference, await measure(page, selectors)), {
					message: `stage layout at ${size.width}x${size.height} matches ${WINDOWS[0].width}x${WINDOWS[0].height}`
				})
				.toBe('');
		}
	} finally {
		await page.setViewportSize(original);
	}
}
