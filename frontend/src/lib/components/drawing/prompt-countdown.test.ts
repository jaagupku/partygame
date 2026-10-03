import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/svelte';
import PromptCountdown from './PromptCountdown.svelte';
import DrawingStage from './DrawingStage.svelte';

afterEach(cleanup);

describe('prompt countdown', () => {
	it('flips changed digits across 100 to 99 and keeps the slot count stable', async () => {
		const screen = render(PromptCountdown, { seconds: 100, paused: false });
		await screen.rerender({ seconds: 99, paused: false });
		expect(screen.container.querySelectorAll('.digit')).toHaveLength(3);
		expect(screen.container.querySelectorAll('.flip-in')).toHaveLength(3);
		expect(screen.getByRole('timer').textContent).toContain('99s');
		expect(screen.getByRole('timer').getAttribute('aria-live')).toBe('off');
	});

	it('alternates accents every eight active ticks without replaying paused or skipped time', async () => {
		const screen = render(PromptCountdown, { seconds: 90, paused: false });
		for (let seconds = 89; seconds >= 82; seconds--)
			await screen.rerender({ seconds, paused: false });
		expect(screen.container.querySelector('.digits.pulse')).not.toBeNull();
		await screen.rerender({ seconds: 82, paused: true });
		expect(screen.container.querySelector('.flip-in')).toBeNull();
		expect(screen.container.querySelector('.digits.pulse')).toBeNull();
		await screen.rerender({ seconds: 82, paused: false });
		expect(screen.container.querySelector('.flip-in')).toBeNull();
		await screen.rerender({ seconds: 50, paused: false });
		expect(screen.container.querySelector('.flip-in')).toBeNull();
		for (let seconds = 49; seconds >= 42; seconds--)
			await screen.rerender({ seconds, paused: false });
		expect(screen.container.querySelector('.digits.slide')).not.toBeNull();
		await screen.rerender({ seconds: 1, paused: false });
		await screen.rerender({ seconds: 0, paused: false });
		expect(screen.getByRole('timer').textContent).toContain('0s');
	});

	it('uses the prominent timer only on the main display during writing', async () => {
		const view: DrawingGameView = {
			phase: 'writing',
			phase_id: 1,
			deadline: Date.now() / 1000 + 90,
			remaining_seconds: null,
			paused: false,
			language: 'en',
			participant_ids: ['p1'],
			ready_ids: [],
			is_participant: false,
			assignments: [],
			matchup_number: 0,
			matchup_count: 0,
			gallery: []
		};
		const screen = render(DrawingStage, { view });
		expect(screen.container.querySelector('.prompt-countdown')).toBeNull();
		await screen.rerender({ view, mainDisplay: true });
		expect(screen.container.querySelector('.prompt-countdown')).not.toBeNull();
		await screen.rerender({ view: { ...view, phase: 'drawing' }, mainDisplay: true });
		expect(screen.container.querySelector('.prompt-countdown')).toBeNull();
	});
});
