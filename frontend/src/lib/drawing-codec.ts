export const DRAWING_CANVAS_WIDTH = 512;
export const DRAWING_CANVAS_HEIGHT = 384;
export const DRAWING_COLORS = [
	'#0f172a',
	'#ef4444',
	'#f97316',
	'#eab308',
	'#22c55e',
	'#06b6d4',
	'#3b82f6',
	'#a855f7',
	'#ec4899',
	'#ffffff'
] as const;

// Normalized canvas-distance tolerance. Higher values reduce more points but can soften curves.
export const STROKE_SIMPLIFICATION_TOLERANCE = 0.005;

function distanceToSegmentSquared(point: DrawingPoint, start: DrawingPoint, end: DrawingPoint) {
	const dx = end.x - start.x;
	const dy = end.y - start.y;
	if (dx === 0 && dy === 0) {
		return Math.hypot(point.x - start.x, point.y - start.y) ** 2;
	}
	const ratio = Math.max(
		0,
		Math.min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / (dx * dx + dy * dy))
	);
	const projectedX = start.x + ratio * dx;
	const projectedY = start.y + ratio * dy;
	return Math.hypot(point.x - projectedX, point.y - projectedY) ** 2;
}

export function simplifyDrawingPoints(
	points: DrawingPoint[],
	tolerance = STROKE_SIMPLIFICATION_TOLERANCE
): DrawingPoint[] {
	if (points.length <= 2) {
		return points.map((point) => ({ x: point.x, y: point.y }));
	}

	const keep = new Set([0, points.length - 1]);
	const toleranceSquared = tolerance * tolerance;
	const stack: Array<[number, number]> = [[0, points.length - 1]];

	while (stack.length > 0) {
		const [startIndex, endIndex] = stack.pop()!;
		let furthestIndex = -1;
		let furthestDistance = 0;
		for (let index = startIndex + 1; index < endIndex; index += 1) {
			const distance = distanceToSegmentSquared(
				points[index],
				points[startIndex],
				points[endIndex]
			);
			if (distance > furthestDistance) {
				furthestDistance = distance;
				furthestIndex = index;
			}
		}
		if (furthestIndex !== -1 && furthestDistance > toleranceSquared) {
			keep.add(furthestIndex);
			stack.push([startIndex, furthestIndex], [furthestIndex, endIndex]);
		}
	}

	return [...keep]
		.toSorted((left, right) => left - right)
		.map((index) => ({ x: points[index].x, y: points[index].y }));
}

export function encodeDrawingSubmission(
	strokes: DrawingStroke[],
	{ simplify = true }: { simplify?: boolean } = {}
): DrawingSubmission {
	return {
		w: DRAWING_CANVAS_WIDTH,
		h: DRAWING_CANVAS_HEIGHT,
		s: strokes.map((stroke) => [
			Math.max(
				0,
				DRAWING_COLORS.indexOf(stroke.color.toLowerCase() as (typeof DRAWING_COLORS)[number])
			),
			stroke.size,
			stroke.eraser ? 1 : 0,
			(simplify ? simplifyDrawingPoints(stroke.points) : stroke.points).flatMap((point) => [
				Math.round(point.x * DRAWING_CANVAS_WIDTH),
				Math.round(point.y * DRAWING_CANVAS_HEIGHT)
			])
		])
	};
}

export function decodeDrawingSubmission(drawing: DrawingSubmission): DrawingStroke[] {
	return drawing.s.map(([colorIndex, size, eraser, coordinates]) => ({
		color: DRAWING_COLORS[colorIndex] ?? DRAWING_COLORS[0],
		size,
		eraser: eraser === 1,
		points: Array.from({ length: Math.floor(coordinates.length / 2) }, (_, index) => ({
			x: (coordinates[index * 2] ?? 0) / DRAWING_CANVAS_WIDTH,
			y: (coordinates[index * 2 + 1] ?? 0) / DRAWING_CANVAS_HEIGHT
		}))
	}));
}
