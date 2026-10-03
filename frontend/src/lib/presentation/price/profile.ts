import type { PresentationProfile } from '../registry';
import StoreDecoration from './StoreDecoration.svelte';
const asset = (name: string, prominent = false) => ({
	src: `/presentation/price/audio/${name}.wav`,
	prominent
});

export const pricePresentation: PresentationProfile = {
	gameType: 'price_guessing',
	appearance: {
		colorScheme: 'light',
		palette: {
			background: '#f8f1df',
			backgroundAlt: '#f0e7cf',
			backgroundWarm: '#fff7e5',
			surface: '#fffaf0',
			surfaceStrong: '#fffdf7',
			border: '#b9c5b5',
			ink: '#183e3a',
			subtle: '#52635b',
			primary: '#17665b',
			primaryStrong: '#104c43',
			accent: '#efbb45',
			accentStrong: '#855900',
			danger: '#b63f32',
			dangerStrong: '#8e2d23'
		},
		tokens: {
			'--presentation-heading-font':
				"'Arial Narrow', 'Liberation Sans Narrow', 'Nunito', sans-serif",
			'--presentation-font': "'Nunito', system-ui, sans-serif",
			'--presentation-card-radius': '0.8rem',
			'--presentation-border-width': '2px',
			'--presentation-card-shadow': '0 5px 0 #183e3a12',
			'--presentation-transition': '180ms ease-out'
		},
		Decoration: StoreDecoration
	},
	audio: {
		music: '/presentation/price/audio/store-loop.wav',
		effects: {
			stepOpen: asset('bag'),
			timerWarning: asset('tick'),
			stepClosed: asset('register'),
			answerReveal: asset('scan', true),
			scoreboardShown: asset('receipt', true),
			finaleReveal: asset('receipt', true),
			finaleStage: asset('chime'),
			winnerPodium: asset('receipt', true),
			checkoutVictory: asset('victory', true),
			checkoutAccepted: asset('confirm')
		}
	},
	adapt(state) {
		const status = 'gameState' in state ? state.gameState : state.state;
		const variant = state.endGame?.revealed
			? 'finale'
			: status === 'waiting_for_players'
				? 'welcome'
				: state.displayPhase === 'answer_reveal'
					? 'checkout'
					: 'browse';
		const cues = [];
		if (state.endGame?.revealed && state.endGame.sequence_stage === 'first_place')
			cues.push({ name: 'checkoutVictory', key: 'winner' });
		// Only public acknowledgement of this phone's action, never a draft or room count.
		if ('gameState' in state && state.hasSubmitted && state.activeStep?.price_mode)
			cues.push({
				name: 'checkoutAccepted',
				key: `${state.activeStep.id}:accepted`,
				audience: 'personal' as const
			});
		return { variant, cues };
	}
};
