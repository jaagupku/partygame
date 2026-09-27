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

function setup(activeStep = step) {
	const onSubmitAnswer = vi.fn();
	const view = render(PlayerInputPanel, {
		activeStep,
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

describe('editable answers', () => {
	it('never sends a partly typed price, including when drafts are collected', async () => {
		const { view, onSubmitAnswer } = setup({ ...step, input_kind: 'number', price_mode: 'guess' });
		for (const value of ['1', '12', '12,', '12,50']) {
			await fireEvent.input(view.getByRole('textbox'), { target: { value } });
			expect(view.component.autosubmitDraft(step.id)).toBe(false);
			expect(onSubmitAnswer).not.toHaveBeenCalled();
		}
		await fireEvent.click(view.getByRole('button'));
		expect(onSubmitAnswer).toHaveBeenCalledWith('12.50');
	});

	it('allows a radio choice to change before and after acknowledgement, but not after closing', async () => {
		const { view, onSubmitAnswer } = setup({
			...step,
			input_kind: 'radio',
			input_options: ['A', 'B']
		});
		await fireEvent.click(view.getByRole('button', { name: 'A' }));
		await fireEvent.click(view.getByRole('button', { name: 'B' }));
		expect(onSubmitAnswer.mock.calls.map(([value]) => value)).toEqual(['A', 'B']);
		await view.rerender({ hasSubmitted: true });
		await fireEvent.click(view.getByRole('button', { name: 'A' }));
		expect(onSubmitAnswer).toHaveBeenLastCalledWith('A');
		await view.rerender({ baseInputDisabled: true });
		expect((view.getByRole('button', { name: 'B' }) as HTMLButtonElement).disabled).toBe(true);
	});

	it('keeps a drawing vote selected and allows a different vote while voting is open', async () => {
		const { view } = setup({ ...step, input_kind: 'drawing', evaluation_type: 'favorite_vote' });
		const onSubmitDrawingVote = vi.fn();
		await view.rerender({
			displayPhase: 'drawing_vote',
			onSubmitDrawingVote,
			drawingItems: [
				{ id: 'a', label: 'A', value: null, vote_count: 0, points_awarded: 0 },
				{ id: 'b', label: 'B', value: null, vote_count: 0, points_awarded: 0 }
			]
		});
		await fireEvent.click(view.getByRole('button', { name: 'A' }));
		await view.rerender({ drawingVotedPlayerIds: ['p1'] });
		expect(view.getByRole('button', { name: 'A' }).getAttribute('aria-pressed')).toBe('true');
		await fireEvent.click(view.getByRole('button', { name: 'B' }));
		expect(onSubmitDrawingVote.mock.calls.map(([value]) => value)).toEqual(['a', 'b']);
		expect(view.getByRole('button', { name: 'B' }).getAttribute('aria-pressed')).toBe('true');
		await view.rerender({ baseInputDisabled: true });
		expect((view.getByRole('button', { name: 'A' }) as HTMLButtonElement).disabled).toBe(true);
	});
});
