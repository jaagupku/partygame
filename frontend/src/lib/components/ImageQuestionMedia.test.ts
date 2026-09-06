import { cleanup, render } from '@testing-library/svelte';
import { tick } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ImageQuestionMedia from './ImageQuestionMedia.svelte';

vi.mock('$app/environment', () => ({ browser: true }));

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
});

describe('image reveal pause rendering', () => {
	it.each(['blur_to_clear', 'blur_circle', 'zoom_out'])(
		'freezes %s and resumes without a backward jump',
		async (reveal) => {
			let now = 105_500;
			vi.spyOn(Date, 'now').mockImplementation(() => now);
			vi.stubGlobal(
				'requestAnimationFrame',
				vi.fn(() => 1)
			);
			vi.stubGlobal('cancelAnimationFrame', vi.fn());
			vi.stubGlobal(
				'ResizeObserver',
				class {
					constructor(private callback: ResizeObserverCallback) {}
					observe(target: Element) {
						this.callback([{ target } as ResizeObserverEntry], this as unknown as ResizeObserver);
					}
					unobserve() {}
					disconnect() {}
				}
			);
			vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(800);
			vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(600);
			const media: RuntimeImageMediaState = {
				type_: 'image',
				src: '/test.png',
				paused: false,
				loop: false,
				reveal,
				reveal_state: 'running',
				reveal_started_at: 100,
				reveal_elapsed_seconds: 0,
				reveal_duration_seconds: 20,
				blur_reveal_curve: [0.5, 0, 1, 1],
				blur_circle_reveal_curve: [0.5, 0, 1, 1]
			};
			const step: RuntimeStepState = {
				id: 'one',
				title: 'Image',
				input_kind: 'buzzer',
				input_enabled: true,
				input_options: [],
				evaluation_type: 'host_judged',
				evaluation_points: 1,
				media,
				timer: { enforced: false, seconds: 20, ends_at: 120 }
			};
			const view = render(ImageQuestionMedia, { step });
			await tick();
			const frame = view.container.querySelector<HTMLElement>('.media-frame')!;
			const image = view.container.querySelector<HTMLElement>('.media-image')!;
			const spotlight = view.container.querySelector<HTMLElement>('.media-spotlight');
			const before = { image: image.style.cssText, circle: spotlight?.style.clipPath };
			const progress = () => Number(frame.style.getPropertyValue('--reveal-progress'));
			expect(progress()).toBeCloseTo(0.275);
			const paused = {
				...step,
				media: {
					...media,
					reveal_state: 'paused',
					reveal_elapsed_seconds: 5.1,
					reveal_started_at: undefined
				},
				timer: { enforced: false, seconds: 20, remaining_seconds: 14.9 }
			};
			await view.rerender({ step: paused });
			expect(progress()).toBeCloseTo(0.275);
			expect(image.style.cssText).toBe(before.image);
			expect(spotlight?.style.clipPath).toBe(before.circle);
			now = 200_000;
			await view.rerender({ step: paused });
			expect(progress()).toBeCloseTo(0.275);
			await view.rerender({
				step: {
					...step,
					media: { ...media, reveal_started_at: 200, reveal_elapsed_seconds: 5.1 },
					timer: { enforced: false, seconds: 20, ends_at: 214.9 }
				}
			});
			expect(progress()).toBeCloseTo(0.275);
			now = 201_000;
			vi.mocked(requestAnimationFrame).mock.calls.at(-1)![0](1000);
			await tick();
			expect(progress()).toBeCloseTo(0.325);
		}
	);
});
