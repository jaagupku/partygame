import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/svelte';
import { tick } from 'svelte';
import DrawingResults from './DrawingResults.svelte';
import { revealElapsed, revealStep, voteStartsAt } from './reveal';
import { locale } from '$lib/i18n';

function view(elapsed = 0): DrawingGameView {
	return {
		phase: 'results',
		phase_id: 4,
		deadline: 1012,
		server_time: 1000 + elapsed,
		reveal_duration: 12,
		remaining_seconds: null,
		paused: false,
		language: 'en',
		participant_ids: ['a', 'b', 'c', 'v1', 'v2'],
		ready_ids: [],
		is_participant: true,
		assignments: [],
		matchup_number: 1,
		matchup_count: 5,
		gallery: [],
		matchup: {
			id: 'match',
			topic: { text: 'Space', fallback: null },
			criterion: { text: 'Funniest', fallback: null },
			drawings: ['a', 'b', 'c'].map((id, i) => ({
				id,
				topic: { text: 'Space', fallback: null },
				value: null,
				revision: 0,
				player_id: id,
				player_name: `Artist ${id}`,
				vote_count: i < 2 ? 1 : 0,
				points: i < 2 ? 500 : 0,
				own: false
			})),
			can_commend_topic: false,
			can_commend_criterion: false,
			topic_author: 'Writer',
			criterion_author: 'Critic',
			topic_points: 20,
			criterion_points: 10,
			allocation: 'votes',
			revealed_votes: [
				{ voter_id: 'v1', voter_name: 'Voter one', drawing_id: 'a' },
				{ voter_id: 'v2', voter_name: 'Voter two', drawing_id: 'b' }
			]
		}
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
	locale.set('en');
});
afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
	vi.useRealTimers();
});

describe('drawing reveal timeline', () => {
	it('uses server time, ignores local wall clock, and freezes the paused elapsed time', () => {
		expect(revealElapsed(view(4))).toBe(4);
		expect(revealElapsed({ ...view(), paused: true, remaining_seconds: 8 })).toBe(4);
		expect(revealElapsed({ ...view(), reveal_duration: null })).toBe(Infinity);
		expect(revealElapsed(view(30))).toBe(12);
	});
	it('sequences votes, exact awards, bonuses and a five-second summary', () => {
		expect(revealStep(0, 12).stage).toBe('revealArtists');
		expect(revealStep(1.5, 12).stage).toBe('revealVotes');
		expect(revealStep(3.5, 12).pointsProgress).toBe(0);
		expect(revealStep(4.5, 12).pointsProgress).toBeGreaterThan(0);
		expect(revealStep(5.5, 12).pointsProgress).toBe(1);
		expect(revealStep(5.5, 12).stage).toBe('revealBonuses');
		expect(revealStep(7, 12).stage).toBe('revealSummary');
		expect(revealStep(9.5, 18, true).pointsProgress).toBe(1);
	});
	it('batches large groups into no more than twelve waves, landing before points start', () => {
		const starts = Array.from({ length: 61 }, (_, i) => voteStartsAt(i, 61, 18));
		expect(new Set(starts).size).toBeLessThanOrEqual(12);
		expect(starts[0]).toBe(1.5);
		expect(starts.at(-1)! + 0.35).toBeLessThan(9.5);
	});
});

describe('drawing results presentation', () => {
	it('reveals each voter on the correct drawing, then awards and bonuses', async () => {
		const component = render(DrawingResults, { view: view() });
		expect(component.queryByText('Voter one')).toBeNull();
		expect(component.container.querySelector('.award')?.getAttribute('aria-hidden')).toBe('true');
		await component.rerender({ view: view(2) });
		expect(component.getByText('Voter one').closest('article')?.dataset.artworkId).toBe('a');
		expect(component.queryByText('Voter two')).toBeNull();
		await component.rerender({ view: view(4.5) });
		expect(component.getByText('Voter two').closest('article')?.dataset.artworkId).toBe('b');
		expect(component.container.querySelector('[data-award="a"]')?.textContent).toContain('+438');
		expect(component.container.querySelector('.bonuses')?.getAttribute('aria-hidden')).toBe('true');
		await component.rerender({ view: view(7) });
		expect(component.container.querySelector('[data-award="a"]')?.textContent).toContain('+500');
		expect(component.container.querySelectorAll('.winner')).toHaveLength(2);
		expect(component.container.querySelector('.bonuses')?.getAttribute('aria-hidden')).toBe(
			'false'
		);
		expect(component.getByText('2 commendations × 10 = +20 points')).toBeTruthy();
	});
	it('resumes on mount and repeated snapshots without rewinding, freezes, then resumes', async () => {
		const component = render(DrawingResults, { view: view(4) });
		expect(component.container.querySelector('.results')?.getAttribute('data-reveal-stage')).toBe(
			'revealPoints'
		);
		await component.rerender({ view: view(0) });
		expect(component.container.querySelector('.results')?.getAttribute('data-reveal-stage')).toBe(
			'revealPoints'
		);
		await component.rerender({
			view: { ...view(4), paused: true, deadline: null, remaining_seconds: 8 }
		});
		const frozen = component.container.querySelector('[data-award="a"]')?.textContent;
		await vi.advanceTimersByTimeAsync(3000);
		await tick();
		expect(component.container.querySelector('[data-award="a"]')?.textContent).toBe(frozen);
		await component.rerender({ view: view(4) });
		await vi.advanceTimersByTimeAsync(3200);
		await tick();
		expect(component.container.querySelector('.results')?.getAttribute('data-reveal-stage')).toBe(
			'revealSummary'
		);
		component.unmount();
		expect(vi.getTimerCount()).toBe(0);
	});
	it('uses immediate exact awards with reduced motion', () => {
		vi.stubGlobal('matchMedia', () => ({
			matches: true,
			addEventListener: vi.fn(),
			removeEventListener: vi.fn()
		}));
		const component = render(DrawingResults, { view: view(3.5) });
		expect(component.container.querySelector('[data-award="a"]')?.textContent).toContain('+500');
		expect(component.container.querySelector('.reduced-motion')).not.toBeNull();
	});
	it('catches up after background suspension and ignores changes to the wall clock', async () => {
		vi.spyOn(performance, 'now').mockReturnValue(0);
		const component = render(DrawingResults, { view: view() });
		vi.setSystemTime(new Date('2040-01-01'));
		vi.mocked(performance.now).mockReturnValue(8000);
		await vi.advanceTimersByTimeAsync(20);
		await tick();
		expect(component.container.querySelector('.results')?.getAttribute('data-reveal-stage')).toBe(
			'revealSummary'
		);
		expect(component.container.querySelector('[data-award="a"]')?.textContent).toContain('+500');
	});
	it('retains every named vote in a large final summary', () => {
		const current = { ...view(18), reveal_duration: 18, deadline: 1018 };
		current.matchup!.revealed_votes = Array.from({ length: 61 }, (_, i) => ({
			voter_id: `v${i}`,
			voter_name: `Voter ${i}`,
			drawing_id: 'a'
		}));
		const component = render(DrawingResults, { view: current });
		expect(component.container.querySelectorAll('[data-voter-id]')).toHaveLength(61);
		expect(component.getByText('61 votes')).toBeTruthy();
	});
	it('keeps legacy results readable without animation metadata', () => {
		const current = view();
		delete current.reveal_duration;
		delete current.matchup!.revealed_votes;
		const component = render(DrawingResults, { view: current });
		expect(component.container.querySelector('.results')?.getAttribute('data-reveal-stage')).toBe(
			'revealSummary'
		);
		expect(component.getAllByText('1 vote')).toHaveLength(2);
		expect(component.container.querySelector('[data-award="a"]')?.textContent).toContain('+500');
	});
	it.each(['uncontested', 'no_votes', 'empty'] as const)(
		'explains %s without invented votes',
		(allocation) => {
			const current = view(7);
			current.matchup!.allocation = allocation;
			current.matchup!.revealed_votes = [];
			if (allocation === 'empty') current.matchup!.drawings = [];
			const component = render(DrawingResults, { view: current });
			expect(component.container.querySelectorAll('[data-voter-id]')).toHaveLength(0);
			expect(component.container.querySelector('.allocation')?.textContent?.trim()).not.toBe('');
		}
	);
});
