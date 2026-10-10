import { describe, expect, it } from 'vitest';
import { resolvePresentation, selectPresentation } from '../registry';
import { presentationVariables } from '../scope';
import { appColorMode } from '$lib/theme';
import { caloriePresentation } from './profile';
import { calorieFinaleReaction, calorieReaction, calorieStageReaction } from './reaction';

const state = (changes = {}) =>
	({
		gameType: 'calorie_guessing',
		gameState: 'running',
		runId: 'one',
		displayPhase: 'question',
		activeStep: { id: 'item', calorie_mode: 'guess' },
		hasSubmitted: false,
		...changes
	}) as ControllerState;

describe('retro studio presentation', () => {
	it('registers Calorie, preserves quiz fallback and keeps every token fixed across app preferences', () => {
		expect(resolvePresentation('calorie_guessing')).toBe(caloriePresentation);
		expect(resolvePresentation('trivia')).toBeUndefined();
		expect(resolvePresentation('unknown')).toBeUndefined();
		const styles = presentationVariables({ gameType: 'calorie_guessing' });
		for (const mode of ['light', 'dark', 'system'] as const) {
			appColorMode.set(mode);
			expect(presentationVariables({ gameType: 'calorie_guessing' })).toEqual(styles);
		}
		expect((styles as Record<string, string>)['--party-surface']).toBe('#fffbf2');
	});
	it('projects the same studio stages for displays and controllers', () => {
		expect(selectPresentation(state({ gameState: 'waiting_for_players' })).variant).toBe('welcome');
		expect(selectPresentation(state()).variant).toBe('thinking');
		expect(selectPresentation(state({ displayPhase: 'answer_reveal' })).variant).toBe('reveal');
		expect(
			selectPresentation({
				game_type: 'calorie_guessing',
				state: 'waiting_for_players'
			} as HostGameState).variant
		).toBe('welcome');
		expect(
			selectPresentation(state({ endGame: { revealed: true, sequence_stage: 'first_place' } }))
		).toMatchObject({
			variant: 'finale',
			cues: [{ name: 'classComplete', key: 'class-complete' }]
		});
	});
	it('ticks under a counting guess reveal only, once per step', () => {
		expect(selectPresentation(state()).cues).toEqual([]);
		expect(selectPresentation(state({ displayPhase: 'answer_reveal' })).cues).toEqual([
			{ name: 'countUp', key: 'item:count-up' }
		]);
		const compare = state({
			displayPhase: 'answer_reveal',
			activeStep: { id: 'pair', calorie_mode: 'compare' }
		});
		expect(selectPresentation(compare).cues).toEqual([]);
	});
	it('never maps room submission sounds, confirms only accepted personal actions with stable keys', () => {
		expect(caloriePresentation.audio?.effects?.submissionReceived).toBeUndefined();
		expect(selectPresentation(state({ submissionCount: 4 })).cues).toEqual([]);
		const accepted = state({ hasSubmitted: true });
		expect(selectPresentation(accepted).cues).toEqual([
			{ name: 'calorieAccepted', key: 'item:accepted', audience: 'personal' }
		]);
		expect(selectPresentation(accepted).cues).toEqual(
			selectPresentation({ ...accepted, lastRevision: 12 }).cues
		);
	});
});

it('bases encouraging reactions only on public scores, with personal feedback isolated', () => {
	const results = [
		{ player_id: 'a', player_name: 'A', answer: 250, points: 900 },
		{ player_id: 'b', player_name: 'B', answer: 1, points: 0 }
	];
	expect(calorieReaction()).toBe('encourage');
	expect(calorieReaction(results)).toBe('close');
	expect(calorieReaction(results, 'a')).toBe('close');
	expect(calorieReaction(results, 'b')).toBe('encourage');
	expect(
		calorieReaction([{ player_id: 'c', player_name: 'C', answer: 300, points: 625 }], 'c')
	).toBe('partial');
	expect(calorieReaction(results, 'missing')).toBe('encourage');
});

it('reacts to final placement on phones and to the podium stage on the display', () => {
	expect(calorieFinaleReaction(1)).toBe('champion');
	expect(calorieFinaleReaction(3)).toBe('podium');
	expect(calorieFinaleReaction(4)).toBe('keepTraining');
	expect(calorieFinaleReaction()).toBe('complete');
	expect(calorieStageReaction('third_place')).toBe('podium');
	expect(calorieStageReaction('first_place')).toBe('champion');
	expect(calorieStageReaction('scoreboard')).toBe('complete');
});
