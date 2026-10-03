import { describe, expect, it } from 'vitest';
import { resolvePresentation, selectPresentation } from '../registry';
import { presentationVariables } from '../scope';
import { appColorMode } from '$lib/theme';
import { pricePresentation } from './profile';

const state = (changes = {}) =>
	({
		gameType: 'price_guessing',
		gameState: 'running',
		runId: 'one',
		displayPhase: 'question',
		activeStep: { id: 'item', price_mode: 'guess' },
		hasSubmitted: false,
		...changes
	}) as ControllerState;

describe('department store presentation', () => {
	it('registers only Price and keeps every token fixed across app preferences', () => {
		expect(resolvePresentation('price_guessing')).toBe(pricePresentation);
		expect(resolvePresentation('trivia')).toBeUndefined();
		expect(resolvePresentation('unknown')).toBeUndefined();
		const styles = presentationVariables({ gameType: 'price_guessing' });
		for (const mode of ['light', 'dark', 'system'] as const) {
			appColorMode.set(mode);
			expect(presentationVariables({ gameType: 'price_guessing' })).toEqual(styles);
		}
		expect((styles as Record<string, string>)['--party-surface']).toBe('#fffaf0');
	});
	it('projects the same shopping stages for displays and controllers', () => {
		expect(selectPresentation(state({ gameState: 'waiting_for_players' })).variant).toBe('welcome');
		expect(selectPresentation(state()).variant).toBe('browse');
		expect(selectPresentation(state({ displayPhase: 'answer_reveal' })).variant).toBe('checkout');
		expect(
			selectPresentation({
				game_type: 'price_guessing',
				state: 'waiting_for_players'
			} as HostGameState).variant
		).toBe('welcome');
		expect(
			selectPresentation(state({ endGame: { revealed: true, sequence_stage: 'first_place' } }))
		).toMatchObject({ variant: 'finale', cues: [{ name: 'checkoutVictory', key: 'winner' }] });
	});
	it('never maps room submission sounds, confirms only accepted personal actions with stable keys', () => {
		expect(pricePresentation.audio?.effects?.submissionReceived).toBeUndefined();
		expect(selectPresentation(state({ submissionCount: 4 })).cues).toEqual([]);
		const accepted = state({ hasSubmitted: true });
		expect(selectPresentation(accepted).cues).toEqual([
			{ name: 'checkoutAccepted', key: 'item:accepted', audience: 'personal' }
		]);
		expect(selectPresentation(accepted).cues).toEqual(
			selectPresentation({ ...accepted, lastRevision: 12 }).cues
		);
	});
});
