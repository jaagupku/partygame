import { describe, expect, it } from 'vitest';
import {
	decodeDrawingSubmission,
	encodeDrawingSubmission,
	simplifyDrawingPoints
} from './drawing-codec';

describe('drawing codec', () => {
	it('simplifies nearly straight strokes while preserving endpoints', () => {
		const points = Array.from({ length: 40 }, (_, index) => ({
			x: index / 39,
			y: index / 39 + (index % 2 === 0 ? 0.001 : -0.001)
		}));

		const simplified = simplifyDrawingPoints(points);

		expect(simplified.length).toBeLessThan(points.length);
		expect(simplified[0]).toEqual(points[0]);
		expect(simplified.at(-1)).toEqual(points.at(-1));
	});

	it('keeps meaningful bends', () => {
		const simplified = simplifyDrawingPoints([
			{ x: 0, y: 0 },
			{ x: 0.5, y: 0.4 },
			{ x: 1, y: 0 }
		]);

		expect(simplified).toHaveLength(3);
	});

	it('encodes simplified strokes as compact drawing arrays', () => {
		const drawing = encodeDrawingSubmission([
			{
				color: '#0f172a',
				size: 8,
				eraser: false,
				points: Array.from({ length: 40 }, (_, index) => ({
					x: index / 39,
					y: index / 39
				}))
			}
		]);

		expect(drawing.w).toBe(512);
		expect(drawing.h).toBe(384);
		expect(drawing.s[0][0]).toBe(0);
		expect(drawing.s[0][2]).toBe(0);
		expect(drawing.s[0][3].length).toBeLessThan(80);
	});

	it('can encode unsimplified strokes for live preview', () => {
		const drawing = encodeDrawingSubmission(
			[
				{
					color: '#0f172a',
					size: 8,
					eraser: false,
					points: Array.from({ length: 40 }, (_, index) => ({
						x: index / 39,
						y: index / 39
					}))
				}
			],
			{ simplify: false }
		);

		expect(drawing.s[0][3]).toHaveLength(80);
	});

	it('decodes compact drawings to editable stroke objects', () => {
		const [stroke] = decodeDrawingSubmission({
			w: 512,
			h: 384,
			s: [[6, 12, 1, [0, 0, 256, 192, 512, 384]]]
		});

		expect(stroke.color).toBe('#3b82f6');
		expect(stroke.size).toBe(12);
		expect(stroke.eraser).toBe(true);
		expect(stroke.points).toEqual([
			{ x: 0, y: 0 },
			{ x: 0.5, y: 0.5 },
			{ x: 1, y: 1 }
		]);
	});
});
