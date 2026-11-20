/** Design size of the main display. Everything inside the stage is authored for this box. */
export const STAGE_WIDTH = 1920;
export const STAGE_HEIGHT = 1080;

/** Largest uniform scale at which the whole stage fits the available area. */
export function stageScale(width: number, height: number) {
	if (!(width > 0) || !(height > 0)) return 0;
	return Math.min(width / STAGE_WIDTH, height / STAGE_HEIGHT);
}
