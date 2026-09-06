import { cleanup, fireEvent, render } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import PlayerInputPanel from './PlayerInputPanel.svelte';

vi.mock('$lib/haptics.js', () => ({ triggerBuzzerHapticPulse: vi.fn() }));

afterEach(cleanup);

const step: RuntimeStepState = {
	id: 'question',
	title: 'Question',
	input_kind: 'text',
	input_enabled: true,
	input_options: [],
	evaluation_type: 'exact_text',
	evaluation_points: 1,
	timer: { enforced: true, seconds: 30, started_at: 100, ends_at: 130 }
};

function setup() {
	const onSubmitAnswer = vi.fn();
	const view = render(PlayerInputPanel, {
		activeStep: step,
		baseInputDisabled: false,
		buzzerActive: false,
		canContinueHostlessInfoSlide: false,
		disabledBuzzerPlayerIds: [],
		displayPhase: 'question_active',
		drawingItems: [],
		drawingVotedPlayerIds: [],
		hasSubmitted: false,
		playerId: 'p1',
		onContinueInfoSlide: vi.fn(),
		onSubmitAnswer,
		onSubmitDrawingVote: vi.fn()
	});
	return { view, onSubmitAnswer };
}

describe('reset question input', () => {
	it('allows a new answer after reset even if the previous submission is still pending', async () => {
		const { view, onSubmitAnswer } = setup();
		await fireEvent.input(view.getByRole('textbox'), { target: { value: 'first answer' } });
		await fireEvent.click(view.getByRole('button'));
		expect(onSubmitAnswer).toHaveBeenCalledWith('first answer');
		expect((view.getByRole('button') as HTMLButtonElement).disabled).toBe(true);
		await view.rerender({
			activeStep: { ...step, timer: { ...step.timer, started_at: 200, ends_at: 230 } }
		});
		expect((view.getByRole('button') as HTMLButtonElement).disabled).toBe(false);
		expect((view.getByRole('textbox') as HTMLInputElement).value).toBe('');
		await fireEvent.input(view.getByRole('textbox'), { target: { value: 'second answer' } });
		await fireEvent.click(view.getByRole('button'));
		expect(onSubmitAnswer).toHaveBeenLastCalledWith('second answer');
		expect(onSubmitAnswer).toHaveBeenCalledTimes(2);
	});

	it('keeps the draft when timing is refreshed or the question closes', async () => {
		const { view } = setup();
		await fireEvent.input(view.getByRole('textbox'), { target: { value: 'draft' } });
		await view.rerender({
			activeStep: { ...step, timer: { ...step.timer, remaining_seconds: 20 } }
		});
		expect((view.getByRole('textbox') as HTMLInputElement).value).toBe('draft');
		await view.rerender({
			activeStep: {
				...step,
				input_enabled: false,
				timer: { enforced: true, seconds: 30, remaining_seconds: 20 }
			},
			baseInputDisabled: true
		});
		expect((view.getByRole('textbox') as HTMLInputElement).value).toBe('draft');
	});
});
