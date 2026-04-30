export const DEFAULT_IMAGE_BLUR_AMOUNT = 18;
export const DEFAULT_BLUR_CIRCLE_START_SIZE = 0.07;
export const BLUR_CIRCLE_END_COVERAGE = 0.92;
export const IMAGE_BLUR_REFERENCE_SIZE = 512;
export const DEFAULT_ZOOM_OUT_START = 2.4;
export const DEFAULT_ZOOM_OUT_ORIGIN_X = 0.58;
export const DEFAULT_ZOOM_OUT_ORIGIN_Y = 0.42;

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
