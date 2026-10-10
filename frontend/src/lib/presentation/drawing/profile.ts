import type { PresentationCue, PresentationProfile } from '../registry';
import SketchDecoration from './SketchDecoration.svelte';
const asset = (name: string, prominent = false) => ({
	src: `/presentation/drawing/audio/${name}.wav`,
	prominent
});

/** From the criterion reveal through results; every showcase returns to the sketchbook. */
const JUDGING_PHASES = new Set(['criterion_reveal', 'voting', 'results']);
const PHASE_CUES: Record<string, string> = {
	writing: 'pageFlip',
	drawing: 'pencilStart',
	showcase: 'pageFlip',
	criterion_reveal: 'criterionReveal',
	voting: 'votingOpen',
	results: 'resultsReveal'
};

export const drawingPresentation: PresentationProfile = {
	gameType: 'drawing_mashup',
	appearance: {
		colorScheme: 'light',
		palette: {
			background: '#fbfaf5',
			backgroundAlt: '#f1efe6',
			backgroundWarm: '#fde7e1',
			surface: '#ffffff',
			surfaceStrong: '#ffffff',
			border: '#c3cadb',
			ink: '#1d2b53',
			subtle: '#4f5a78',
			primary: '#2a4a9b',
			primaryStrong: '#1d2b53',
			accent: '#f26b5b',
			accentStrong: '#b4382b',
			danger: '#b3261e',
			dangerStrong: '#8c1d18'
		},
		tokens: {
			'--presentation-heading-font': "'Caveat', 'Baloo 2', cursive",
			'--presentation-font': "'Nunito', system-ui, sans-serif",
			'--presentation-card-radius': '0.6rem',
			'--presentation-border-width': '2px',
			'--presentation-card-shadow': '3px 4px 0 #1d2b5314',
			'--presentation-transition': '180ms ease-out'
		},
		Decoration: SketchDecoration
	},
	variants: {
		judging: {
			appearance: {
				colorScheme: 'dark',
				palette: {
					background: '#3b1470',
					backgroundAlt: '#4b1c8c',
					backgroundWarm: '#5a2399',
					surface: '#4a1d86',
					surfaceStrong: '#5b27a0',
					border: '#a283e0',
					ink: '#fffbea',
					subtle: '#e4d7ff',
					primary: '#ffd23f',
					primaryStrong: '#ffe27a',
					accent: '#ffd23f',
					accentStrong: '#f5b700',
					danger: '#ff8a80',
					dangerStrong: '#ffb4ab'
				},
				tokens: {
					'--presentation-heading-font': "'Barlow Condensed', 'Baloo 2', sans-serif",
					'--presentation-card-shadow': '0 0 0 3px #ffd23f33, 0 10px 30px #12002b66'
				}
			},
			music: '/presentation/drawing/audio/judging-loop.wav'
		}
	},
	audio: {
		music: '/presentation/drawing/audio/sketch-loop.wav',
		effects: {
			pageFlip: asset('page-flip'),
			pencilStart: asset('pencil'),
			criterionReveal: asset('twist', true),
			votingOpen: asset('vote-open'),
			resultsReveal: asset('results', true),
			revealVotes: asset('tally'),
			revealPoints: asset('points', true),
			revealBonuses: asset('bonus'),
			timerWarning: asset('warning'),
			timerTick: asset('tick'),
			finaleReveal: asset('fanfare', true),
			finaleStage: asset('stage'),
			winnerPodium: asset('fanfare', true),
			drawingReady: asset('confirm')
		}
	},
	adapt(state) {
		const status = 'gameState' in state ? state.gameState : state.state;
		const view = state.drawingGame;
		const phase = view?.phase ?? '';
		const variant =
			status === 'waiting_for_players'
				? 'welcome'
				: JUDGING_PHASES.has(phase)
					? 'judging'
					: 'sketchbook';
		const cues: PresentationCue[] = [];
		if (view && PHASE_CUES[phase])
			cues.push({ name: PHASE_CUES[phase], key: `${view.phase_id}:${phase}` });
		// Only the player's own accepted "done"; strokes and autosaves never make a sound.
		if (
			'gameState' in state &&
			view &&
			['writing', 'drawing', 'voting'].includes(phase) &&
			view.ready_ids.includes(state.id)
		)
			cues.push({ name: 'drawingReady', key: `${view.phase_id}:ready`, audience: 'personal' });
		return { variant, cues };
	}
};
