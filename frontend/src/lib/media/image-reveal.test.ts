import { describe, expect, it } from 'vitest';
import {
	createRevealProgressTracker,
	getImageRevealProgress,
	mapRevealProgress,
	normalizeRevealCurve
} from './image-reveal';

describe('image reveal curves', () => {
	it('defaults to linear progress when no curve is stored', () => {
		expect(mapRevealProgress(0.25)).toBeCloseTo(0.25, 5);
		expect(mapRevealProgress(0.75, [0, 0, 1, 1])).toBeCloseTo(0.75, 5);
	});

	it('clamps progress and curve values to the 0..1 range', () => {
		expect(mapRevealProgress(-1)).toBe(0);
		expect(mapRevealProgress(2)).toBe(1);
		expect(normalizeRevealCurve([-0.2, 0.4, 1.4, 0.8])).toEqual([0, 0.4, 1, 0.8]);
	});

	it('maps progress through non-linear cubic-bezier curves', () => {
		expect(mapRevealProgress(0.25, [0.5, 0, 1, 1])).toBeLessThan(0.25);
		expect(mapRevealProgress(0.75, [0, 0, 0.5, 1])).toBeGreaterThan(0.75);
	});
});

describe('reveal pause continuity', () => {
	it('holds the displayed progress through delayed pause updates and resumes smoothly', () => {
		const track = createRevealProgressTracker();
		expect(track('image', 'running', 0.45)).toBe(0.45);
		expect(track('image', 'paused', 0.41)).toBe(0.45);
		expect(track('image', 'paused', 0.41)).toBe(0.45);
		expect(track('image', 'running', 0.42)).toBe(0.45);
		expect(track('image', 'running', 0.47)).toBeCloseTo(0.5);
		expect(track('image', 'paused', 0.46)).toBeCloseTo(0.5);
		expect(track('image', 'running', 0.46)).toBeCloseTo(0.5);
		expect(track('image', 'running', 0.56)).toBeCloseTo(0.6);
	});

	it('uses saved timing when first opening a paused image and resets for another image', () => {
		const track = createRevealProgressTracker();
		expect(track('image', 'paused', 0.4)).toBe(0.4);
		expect(track('next', 'running', 0.01)).toBe(0.01);
		expect(track('next', 'revealed', 0.5)).toBe(1);
		expect(track('next', 'idle', 0)).toBe(0);
	});

	it('does not jump forward on pause when the browser clock was behind', () => {
		const track = createRevealProgressTracker();
		track('image', 'running', 0.4);
		expect(track('image', 'paused', 0.45)).toBe(0.4);
		expect(track('image', 'running', 0.46)).toBe(0.4);
		expect(track('image', 'running', 0.56)).toBeCloseTo(0.5);
		expect(track('image', 'revealed', 1)).toBe(1);
	});

	it('reads fractional timer timing and falls back to media timing for untimed steps', () => {
		const media: RuntimeImageMediaState = {
			type_: 'image',
			src: '/image.png',
			paused: false,
			loop: false,
			reveal_state: 'running',
			reveal_started_at: 100,
			reveal_elapsed_seconds: 2,
			reveal_duration_seconds: 20
		};
		expect(
			getImageRevealProgress(
				{ media, timer: { enforced: false, seconds: 20, ends_at: 120 } },
				105_500
			)
		).toBeCloseTo(0.275);
		expect(getImageRevealProgress({ media, timer: { enforced: false } }, 105_500)).toBeCloseTo(
			0.375
		);
		expect(
			getImageRevealProgress(
				{
					media: { ...media, reveal_state: 'paused', reveal_elapsed_seconds: 7.5 },
					timer: { enforced: false }
				},
				200_000
			)
		).toBeCloseTo(0.375);
	});
});
