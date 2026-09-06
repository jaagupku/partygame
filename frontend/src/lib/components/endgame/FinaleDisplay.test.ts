import { cleanup, render } from '@testing-library/svelte';
import { afterEach, describe, expect, it } from 'vitest';
import FinaleDisplay from './FinaleDisplay.svelte';

afterEach(cleanup);

const cards: EndGameStatCard[] = [
	{
		id: 'highest_accuracy',
		label: '',
		winner_player_ids: ['p1', 'p2'],
		value: 80,
		unit: 'percent',
		answer_counts: { p1: 10, p2: 5 },
		correct_counts: { p1: 8, p2: 4 }
	},
	{ id: 'team_correct', label: '', winner_player_ids: [], value: 12, unit: 'answers' },
	{
		id: 'game_mood',
		label: '',
		winner_player_ids: [],
		value: 13,
		unit: 'uses',
		emoji: '😂',
		reaction_key: 'laugh'
	},
	{ id: 'most_wrong', label: '', winner_player_ids: ['p1'], value: 10 },
	{
		id: 'signature_reaction',
		label: '',
		winner_player_ids: ['p1'],
		value: 13,
		unit: 'uses',
		emoji: '😂',
		reaction_key: 'laugh'
	}
];
const endGame: EndGameState = {
	revealed: true,
	sequence_stage: 'stats',
	autoplay_enabled: false,
	final_standings: [],
	podium: [],
	stats_cards: cards,
	highlight_card_ids: ['highest_accuracy', 'team_correct', 'game_mood']
};

describe('finale highlights', () => {
	it('shows only the selected three cards with separate units and explicit ties', () => {
		const view = render(FinaleDisplay, {
			endGame,
			players: [],
			playerMap: new Map(),
			title: 'Showcase'
		});
		expect(view.container.querySelectorAll('.stat-card')).toHaveLength(3);
		expect(view.getByText('Shared award')).toBeTruthy();
		expect(view.getByText('p1: 8 of 10 correct')).toBeTruthy();
		expect(view.getByText('p2: 4 of 5 correct')).toBeTruthy();
		expect(view.getByText('13').classList.contains('stat-value')).toBe(true);
		expect(view.getByText('uses').classList.contains('stat-unit')).toBe(true);
		expect(view.queryByText('Most wrong')).toBeNull();
		expect(view.queryByText('Signature Reaction')).toBeNull();
	});

	it('renders an honest empty state when no facts are available', () => {
		const view = render(FinaleDisplay, {
			endGame: { ...endGame, stats_cards: [], highlight_card_ids: [] },
			players: [],
			playerMap: new Map()
		});
		expect(view.getByText('No Stats Yet')).toBeTruthy();
	});

	it('keeps a compact highlight recap with the final scoreboard', () => {
		const view = render(FinaleDisplay, {
			endGame: { ...endGame, sequence_stage: 'scoreboard' },
			players: [],
			playerMap: new Map()
		});
		expect(
			view.getByRole('complementary', { name: 'Match highlights' }).querySelectorAll('p')
		).toHaveLength(3);
		expect(view.container.querySelectorAll('.stat-card')).toHaveLength(0);
	});
});
