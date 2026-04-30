export const DEFAULT_IMAGE_BLUR_AMOUNT = 18;
export const DEFAULT_BLUR_CIRCLE_START_SIZE = 0.07;
export const BLUR_CIRCLE_END_COVERAGE = 0.92;
export const IMAGE_BLUR_REFERENCE_SIZE = 512;
export const DEFAULT_ZOOM_OUT_START = 2.4;
export const DEFAULT_ZOOM_OUT_ORIGIN_X = 0.58;
export const DEFAULT_ZOOM_OUT_ORIGIN_Y = 0.42;
export const DEFAULT_REVEAL_CURVE: RevealCurve = [0, 0, 1, 1];

function clampProgress(value: number): number {
	if (!Number.isFinite(value)) {
		return 0;
	}
	return Math.min(1, Math.max(0, value));
}

function cubicBezierAxis(t: number, point1: number, point2: number): number {
	const inverse = 1 - t;
	return 3 * inverse * inverse * t * point1 + 3 * inverse * t * t * point2 + t * t * t;
}

function cubicBezierAxisDerivative(t: number, point1: number, point2: number): number {
	const inverse = 1 - t;
	return (
		3 * inverse * inverse * point1 + 6 * inverse * t * (point2 - point1) + 3 * t * t * (1 - point2)
	);
}

export function normalizeRevealCurve(curve?: RevealCurve | null): RevealCurve {
	if (!curve || curve.length !== 4) {
		return [...DEFAULT_REVEAL_CURVE];
	}
	return curve.map(clampProgress) as RevealCurve;
}

export function mapRevealProgress(progress: number, curve?: RevealCurve | null): number {
	const [x1, y1, x2, y2] = normalizeRevealCurve(curve);
	const x = clampProgress(progress);
	if (x1 === 0 && y1 === 0 && x2 === 1 && y2 === 1) {
		return x;
	}

	let t = x;
	for (let i = 0; i < 8; i += 1) {
		const currentX = cubicBezierAxis(t, x1, x2) - x;
		const derivative = cubicBezierAxisDerivative(t, x1, x2);
		if (Math.abs(currentX) < 0.000001 || Math.abs(derivative) < 0.000001) {
			break;
		}
		t = clampProgress(t - currentX / derivative);
	}

	let lower = 0;
	let upper = 1;
	for (let i = 0; i < 12; i += 1) {
		const currentX = cubicBezierAxis(t, x1, x2);
		if (Math.abs(currentX - x) < 0.000001) {
			break;
		}
		if (currentX < x) {
			lower = t;
		} else {
			upper = t;
		}
		t = (lower + upper) / 2;
	}

	return clampProgress(cubicBezierAxis(t, y1, y2));
}

export function getScaledImageBlurAmount(
	blurAmount: number,
	width: number,
	height: number
): number {
	const minDimension = Math.min(width, height);
	if (minDimension <= 0) {
		return blurAmount;
	}
	return blurAmount * (minDimension / IMAGE_BLUR_REFERENCE_SIZE);
}

export function getBlurCircleRadius(
	startSize: number,
	progress: number,
	width: number,
	height: number
): number {
	const minDimension = Math.min(width, height);
	if (minDimension <= 0) {
		return 0;
	}
	const startRadius = minDimension * startSize;
	const endRadius = (Math.hypot(width, height) / 2) * BLUR_CIRCLE_END_COVERAGE;
	return startRadius + Math.max(0, endRadius - startRadius) * progress;
}
