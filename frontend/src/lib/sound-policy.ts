import type { SoundCue } from '$lib/sound-detector.js';

export type SoundSurface = 'host-display' | 'controller';

export type SoundSettings = {
	soundEnabled: boolean;
	masterVolume: number;
};

export const DEFAULT_SOUND_SETTINGS: Record<SoundSurface, SoundSettings> = {
	'host-display': {
		soundEnabled: true,
		masterVolume: 0.78
	},
	controller: {
		soundEnabled: false,
		masterVolume: 0.35
	}
};

const ALLOWED_CUES: Record<SoundSurface, Set<SoundCue>> = {
	'host-display': new Set([
		'buzz',
		'correct',
		'wrong',
		'stepOpen',
		'answerReveal',
		'buzzerArmed',
		'timerWarning',
		'stepClosed',
		'scoreboardShown',
		'finaleReveal',
		'finaleStage',
		'winnerPodium'
	]),
	controller: new Set(['submissionReceived', 'pendingReviewCleared'])
};

export function createSoundPolicy(
	surface: SoundSurface,
	settings = DEFAULT_SOUND_SETTINGS[surface]
) {
	return {
		settings,
		shouldPlay(cue: SoundCue) {
			return settings.soundEnabled && ALLOWED_CUES[surface].has(cue);
		}
	};
}
