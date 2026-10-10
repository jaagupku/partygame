import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render } from '@testing-library/svelte';
import { tick } from 'svelte';
import DrawingPlayer from './DrawingPlayer.svelte';
import DrawingResults from './DrawingResults.svelte';
import DrawingStage from './DrawingStage.svelte';
import { INTRO_SECONDS, isIntroPhase, serverRemaining } from './reveal';
import { locale } from '$lib/i18n';

const artwork = (id: string): MashupArtwork => ({
	id,
	topic: { text: 'A rainy picnic', fallback: null },
	value: null,
	revision: 0,
	vote_count: 0,
	points: 0,
	own: false
});
function intro(phase: 'showcase' | 'criterion_reveal' | 'voting', changes = {}): DrawingGameView {
	return {
		phase,
		phase_id: phase === 'showcase' ? 3 : phase === 'criterion_reveal' ? 4 : 5,
		deadline: 1004,
		server_time: 1000,
		remaining_seconds: null,
		paused: false,
		language: 'en',
		participant_ids: ['p1', 'p2', 'p3'],
		ready_ids: [],
		is_participant: true,
		assignments: [],
		matchup_number: 1,
		matchup_count: 3,
		gallery: [],
		matchup: {
			id: 'match',
			topic: { text: 'A rainy picnic', fallback: null },
			criterion:
				phase === 'showcase' ? null : { text: 'Most likely to win a medal', fallback: null },
			drawings: [artwork('a'), artwork('b')],
			can_commend_topic: phase === 'voting',
			can_commend_criterion: phase === 'voting',
			topic_points: 0,
			criterion_points: 0
		},
		...changes
	};
}

beforeEach(() => {
	vi.useFakeTimers();
	vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
	vi.stubGlobal('matchMedia', () => ({
		matches: false,
		addEventListener: vi.fn(),
		removeEventListener: vi.fn()
	}));
	localStorage.clear();
	locale.set('en');
});
afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
	vi.useRealTimers();
});

describe('matchup introduction', () => {
	it('keeps fixed stage lengths and reads progress from the server clock', () => {
		expect(INTRO_SECONDS).toEqual({ showcase: 4, criterion_reveal: 2 });
		expect(isIntroPhase('showcase') && isIntroPhase('criterion_reveal')).toBe(true);
		expect(isIntroPhase('voting')).toBe(false);
		vi.setSystemTime(5_000_000);
		expect(serverRemaining(intro('showcase', { server_time: 1001 }))).toBe(3);
		expect(
			serverRemaining(intro('showcase', { paused: true, deadline: null, remaining_seconds: 2.5 }))
		).toBe(2.5);
	});

	it('shows the topic and artwork with a sealed criterion during the showcase', () => {
		const { container, getByRole, queryByText } = render(DrawingStage, {
			view: intro('showcase', { server_time: 1001 }),
			mainDisplay: true
		});
		expect(container.querySelector('[data-drawing-stage="showcase"]')).toBeTruthy();
		expect(container.textContent).toContain('A rainy picnic');
		expect(container.querySelectorAll('.drawing-artwork')).toHaveLength(2);
		expect(container.querySelector('.drawing-criterion-sealed')).toBeTruthy();
		expect(queryByText('Most likely to win a medal')).toBeNull();
		const progress = getByRole('progressbar');
		expect(progress.getAttribute('aria-valuemax')).toBe('4');
		expect(progress.getAttribute('aria-valuenow')).toBe('1');
		const fill = progress.firstElementChild as HTMLElement;
		expect(fill.style.getPropertyValue('--intro-from')).toBe('0.25');
		expect(fill.style.getPropertyValue('--intro-duration')).toBe('3s');
		// Ready counts belong to voting; the introduction has no player action.
		expect(container.textContent).not.toContain('Players ready');
	});

	it('reveals the plot twist around artwork that stays in place', async () => {
		const view = intro('showcase');
		const { container, rerender } = render(DrawingStage, { view, mainDisplay: true });
		const before = [...container.querySelectorAll('.drawing-artwork')];
		await rerender({ view: intro('criterion_reveal', { deadline: 1006, server_time: 1004 }) });
		expect(container.querySelector('.drawing-criterion-sealed')).toBeNull();
		const twist = container.querySelector('.drawing-twist');
		expect(twist?.textContent).toContain('Plot twist!');
		expect(twist?.textContent).toContain('Most likely to win a medal');
		expect(container.textContent).toContain('A rainy picnic');
		// The same artwork elements remain mounted through the transformation.
		expect([...container.querySelectorAll('.drawing-artwork')]).toEqual(before);
	});

	it('freezes the progress and animations while paused', () => {
		const { container, getByText } = render(DrawingStage, {
			view: intro('criterion_reveal', { paused: true, deadline: null, remaining_seconds: 1 })
		});
		expect(container.querySelector('.drawing-stage-paused')).toBeTruthy();
		expect(getByText('Game paused')).toBeTruthy();
		const fill = container.querySelector('.drawing-intro-progress > span') as HTMLElement;
		expect(fill.style.getPropertyValue('--intro-from')).toBe('0.5');
	});

	it('keeps voting controls unavailable on phones until voting opens', async () => {
		const send = vi.fn();
		const { container, queryAllByRole, queryByText, getByRole, rerender } = render(DrawingPlayer, {
			view: intro('showcase'),
			runId: 'run',
			playerId: 'p1',
			organizer: false,
			connected: true,
			send
		});
		for (const view of [intro('showcase'), intro('criterion_reveal')]) {
			await rerender({ view });
			expect(container.querySelector(`[data-drawing-stage="${view.phase}"]`)).toBeTruthy();
			expect(queryAllByRole('button', { name: /^Commend/ })).toHaveLength(0);
			expect(queryByText('Abstain')).toBeNull();
			expect(queryByText('Done')).toBeNull();
		}
		await vi.advanceTimersByTimeAsync(500);
		expect(send).not.toHaveBeenCalled();
		await rerender({ view: intro('voting', { deadline: 1036 }) });
		expect(queryByText('Abstain')).toBeTruthy();
		const thumbs = queryAllByRole('button', { name: /^Commend/ });
		expect(thumbs).toHaveLength(2);
		const topic = getByRole('button', { name: 'Commend the topic (+10)' });
		expect(topic.getAttribute('aria-pressed')).toBe('false');
		await fireEvent.click(topic);
		expect(topic.getAttribute('aria-pressed')).toBe('true');
		expect(topic.classList.contains('on')).toBe(true);
	});
});

describe('shared display cues', () => {
	function writing(secondsLeft: number): DrawingGameView {
		return {
			...intro('voting'),
			phase: 'writing',
			phase_id: 1,
			matchup: null,
			deadline: Date.now() / 1000 + secondsLeft
		};
	}

	it('plays countdown warnings only for a countdown observed live', async () => {
		vi.setSystemTime(1_000_000);
		const oncue = vi.fn();
		render(DrawingStage, { view: writing(7), mainDisplay: true, oncue });
		await vi.advanceTimersByTimeAsync(2_200);
		expect(oncue).toHaveBeenCalledWith('timerWarning', '1:countdown:5');
		await vi.advanceTimersByTimeAsync(5_000);
		expect(oncue.mock.calls.map(([, key]) => key)).toEqual([
			'1:countdown:5',
			'1:countdown:3',
			'1:countdown:2',
			'1:countdown:1'
		]);
		cleanup();
		// Arriving with two seconds left skips the warnings that were missed.
		const late = vi.fn();
		render(DrawingStage, { view: writing(2), mainDisplay: true, oncue: late });
		await tick();
		expect(late).not.toHaveBeenCalled();
		await vi.advanceTimersByTimeAsync(1_200);
		expect(late.mock.calls).toEqual([['timerTick', '1:countdown:1']]);
	});

	it('marks results milestones as they are reached, not on a mid-reveal reload', async () => {
		const results = (elapsed: number): DrawingGameView => ({
			...intro('voting'),
			phase: 'results',
			phase_id: 6,
			deadline: 1012,
			server_time: 1000 + elapsed,
			reveal_duration: 12,
			matchup: {
				...intro('voting').matchup!,
				drawings: [artwork('a'), artwork('b')].map((art) => ({ ...art, player_name: art.id })),
				revealed_votes: [{ voter_id: 'v', voter_name: 'V', drawing_id: 'a' }],
				allocation: 'votes'
			}
		});
		const oncue = vi.fn();
		render(DrawingResults, { view: results(0), oncue });
		await tick();
		expect(oncue).not.toHaveBeenCalled();
		await vi.advanceTimersByTimeAsync(1_700);
		expect(oncue).toHaveBeenCalledWith('revealVotes', '6:revealVotes');
		cleanup();
		const reloaded = vi.fn();
		render(DrawingResults, { view: results(4), oncue: reloaded });
		await tick();
		expect(reloaded).not.toHaveBeenCalled();
	});
});
