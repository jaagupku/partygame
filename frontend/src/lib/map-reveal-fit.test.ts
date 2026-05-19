import { describe, expect, it } from 'vitest';
import { buildMapRevealFitTarget, revealFitKey } from './map-reveal-fit';

describe('map reveal fit helpers', () => {
	it('builds a point target for a single reveal point', () => {
		const target = buildMapRevealFitTarget([], { lat: 48.8606, lng: 2.3376 }, { maxZoom: 18 });

		expect(target).toEqual({
			kind: 'point',
			point: { lat: 48.8606, lng: 2.3376 },
			zoom: 16
		});
	});

	it('builds a padded bounds target for guesses and the correct point', () => {
		const target = buildMapRevealFitTarget(
			[{ point: { lat: 48.86, lng: 2.33 } }, { point: { lat: 48.87, lng: 2.35 } }],
			{ lat: 48.8606, lng: 2.3376 },
			{ maxZoom: 17, padding: [64, 64] }
		);

		expect(target).toEqual({
			kind: 'bounds',
			points: [
				{ lat: 48.86, lng: 2.33 },
				{ lat: 48.87, lng: 2.35 },
				{ lat: 48.8606, lng: 2.3376 }
			],
			padding: [64, 64],
			maxZoom: 17
		});
	});

	it('uses a stable fit key regardless of point order', () => {
		const first = revealFitKey([
			{ lat: 48.87, lng: 2.35 },
			{ lat: 48.86, lng: 2.33 }
		]);
		const second = revealFitKey([
			{ lat: 48.86, lng: 2.33 },
			{ lat: 48.87, lng: 2.35 }
		]);

		expect(first).toBe(second);
	});
});
