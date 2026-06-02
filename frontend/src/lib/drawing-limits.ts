export const DRAWING_LIMITS = {
	maxStrokes: 320,
	maxPoints: 6_400,
	maxPayloadChars: 240_000,
	warningRatio: 0.8
} as const;

export type DrawingLimitUsage = {
	strokes: number;
	points: number;
	payloadChars: number;
	maxRatio: number;
	overLimit: boolean;
	nearLimit: boolean;
};

export function getDrawingLimitUsage(drawing: DrawingSubmission): DrawingLimitUsage {
	const strokes = drawing.s.length;
	const points = drawing.s.reduce((total, stroke) => total + Math.floor(stroke[3].length / 2), 0);
	const payloadChars = JSON.stringify(drawing).length;
	const maxRatio = Math.max(
		strokes / DRAWING_LIMITS.maxStrokes,
		points / DRAWING_LIMITS.maxPoints,
		payloadChars / DRAWING_LIMITS.maxPayloadChars
	);
	const overLimit =
		strokes > DRAWING_LIMITS.maxStrokes ||
		points > DRAWING_LIMITS.maxPoints ||
		payloadChars > DRAWING_LIMITS.maxPayloadChars;

	return {
		strokes,
		points,
		payloadChars,
		maxRatio,
		overLimit,
		nearLimit: !overLimit && maxRatio >= DRAWING_LIMITS.warningRatio
	};
}
