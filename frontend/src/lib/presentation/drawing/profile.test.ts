import { describe, expect, it } from 'vitest';
import { resolvePresentation, selectPresentation } from '../registry';
import { presentationVariables } from '../scope';
import { appColorMode } from '$lib/theme';
import { drawingPresentation } from './profile';

const drawing = (phase: DrawingGameView['phase'], changes: Partial<DrawingGameView> = {}) =>
	({ phase, phase_id: 7, ready_ids: [], ...changes }) as DrawingGameView;
const controller = (changes = {}) =>
	({
		gameType: 'drawing_mashup',
		gameState: 'running',
		runId: 'one',
		id: 'p1',
		...changes
	}) as ControllerState;
const display = (changes = {}) =>
	({ game_type: 'drawing_mashup', state: 'running', run_id: 'one', ...changes }) as HostGameState;

describe('sketchbook presentation', () => {
	it('registers Drawing Mashup and keeps both variants fixed across app preferences', () => {
		expect(resolvePresentation('drawing_mashup')).toBe(drawingPresentation);
		expect(resolvePresentation('trivia')).toBeUndefined();
		for (const variant of [undefined, 'judging']) {
			const styles = presentationVariables({ gameType: 'drawing_mashup', variant });
			for (const mode of ['light', 'dark', 'system'] as const) {
				appColorMode.set(mode);
				expect(presentationVariables({ gameType: 'drawing_mashup', variant })).toEqual(styles);
			}
		}
		const paper = presentationVariables({ gameType: 'drawing_mashup' }) as Record<string, string>;
		const stage = presentationVariables({
			gameType: 'drawing_mashup',
			variant: 'judging'
		}) as Record<string, string>;
		expect(paper['--party-surface']).toBe('#ffffff');
		expect(stage['--party-surface']).toBe('#4a1d86');
		expect(stage['--party-accent']).toBe('#ffd23f');
	});

	it('switches to the judging stage at the criterion reveal and back for the next showcase', () => {
		expect(selectPresentation(display({ state: 'waiting_for_players' })).variant).toBe('welcome');
		const variants = Object.fromEntries(
			(
				[
					'writing',
					'drawing',
					'showcase',
					'criterion_reveal',
					'voting',
					'results',
					'finished'
				] as const
			).map((phase) => [
				phase,
				selectPresentation(display({ drawingGame: drawing(phase) })).variant
			])
		);
		expect(variants).toEqual({
			writing: 'sketchbook',
			drawing: 'sketchbook',
			showcase: 'sketchbook',
			criterion_reveal: 'judging',
			voting: 'judging',
			results: 'judging',
			finished: 'sketchbook'
		});
		// Phones follow the same variant from their own projection.
		expect(
			selectPresentation(controller({ drawingGame: drawing('criterion_reveal') })).variant
		).toBe('judging');
		expect(drawingPresentation.variants?.judging.music).toContain('judging-loop');
		expect(drawingPresentation.audio?.music).toContain('sketch-loop');
	});

	it('keys each stage cue by phase so reconnects and repeats never replay the sting', () => {
		const reveal = selectPresentation(display({ drawingGame: drawing('criterion_reveal') }));
		expect(reveal.cues).toEqual([{ name: 'criterionReveal', key: '7:criterion_reveal' }]);
		expect(drawingPresentation.audio?.effects?.criterionReveal.prominent).toBe(true);
		expect(
			selectPresentation(display({ drawingGame: drawing('criterion_reveal'), lastRevision: 9 }))
				.cues
		).toEqual(reveal.cues);
		expect(selectPresentation(display()).cues).toEqual([]);
	});

	it('confirms only the player’s own accepted ready action, never progress or strokes', () => {
		const ready = drawing('drawing', { ready_ids: ['p2'] });
		expect(selectPresentation(controller({ drawingGame: ready })).cues).toEqual([
			{ name: 'pencilStart', key: '7:drawing' }
		]);
		expect(
			selectPresentation(controller({ drawingGame: { ...ready, ready_ids: ['p2', 'p1'] } })).cues
		).toContainEqual({ name: 'drawingReady', key: '7:ready', audience: 'personal' });
		expect(drawingPresentation.audio?.effects?.submissionReceived).toBeUndefined();
	});
});
