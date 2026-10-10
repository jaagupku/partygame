import type { PresentationProfile } from '../registry';
import StudioDecoration from './StudioDecoration.svelte';
const asset = (name: string, prominent = false) => ({
	src: `/presentation/calorie/audio/${name}.wav`,
	prominent
});

export const caloriePresentation: PresentationProfile = {
	gameType: 'calorie_guessing',
	appearance: {
		colorScheme: 'light',
		palette: {
			background: '#fff4df',
			backgroundAlt: '#ede0f3',
			backgroundWarm: '#ffe4d8',
			surface: '#fffbf2',
			surfaceStrong: '#ffffff',
			border: '#b8a9c6',
			ink: '#34234e',
			subtle: '#63556f',
			primary: '#654399',
			primaryStrong: '#4c2c7c',
			accent: '#37c3b5',
			accentStrong: '#126c65',
			danger: '#b33832',
			dangerStrong: '#872921'
		},
		tokens: {
			'--presentation-heading-font': "'Baloo 2', 'Nunito', system-ui, sans-serif",
			'--presentation-font': "'Nunito', system-ui, sans-serif",
			'--presentation-card-radius': '1.5rem',
			'--presentation-border-width': '2px',
			'--presentation-card-shadow': '0 5px 0 #65439918',
			'--presentation-transition': '180ms ease-out'
		},
		Decoration: StudioDecoration
	},
	audio: {
		music: '/presentation/calorie/audio/studio-loop.wav',
		effects: {
			stepOpen: asset('whistle'),
			timerWarning: asset('interval'),
			stepClosed: asset('stop'),
			answerReveal: asset('reveal', true),
			countUp: asset('count'),
			scoreboardShown: asset('milestone', true),
			finaleReveal: asset('milestone', true),
			finaleStage: asset('stage'),
			classComplete: asset('complete', true),
			calorieAccepted: asset('confirm')
		}
	},
	adapt(state) {
		const status = 'gameState' in state ? state.gameState : state.state;
		const variant = state.endGame?.revealed
			? 'finale'
			: status === 'waiting_for_players'
				? 'welcome'
				: state.displayPhase === 'answer_reveal'
					? 'reveal'
					: 'thinking';
		const cues = [];
		if (state.endGame?.revealed && state.endGame.sequence_stage === 'first_place')
			cues.push({ name: 'classComplete', key: 'class-complete' });
		// Ticks under the calorie count climbing; the asset leads in under `reveal`.
		if (state.displayPhase === 'answer_reveal' && state.activeStep?.calorie_mode === 'guess')
			cues.push({ name: 'countUp', key: `${state.activeStep.id}:count-up` });
		if ('gameState' in state && state.hasSubmitted && state.activeStep?.calorie_mode)
			cues.push({
				name: 'calorieAccepted',
				key: `${state.activeStep.id}:accepted`,
				audience: 'personal' as const
			});
		return { variant, cues };
	}
};
