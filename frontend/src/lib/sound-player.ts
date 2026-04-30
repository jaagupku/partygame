import { browser } from '$app/environment';
import answerRevealWav from '$lib/assets/sounds/answer-reveal.wav';
import buzzerArmedWav from '$lib/assets/sounds/buzzer-armed.wav';
import buzzerOgg from '$lib/assets/sounds/buzzer.ogg';
import correctWav from '$lib/assets/sounds/correct.wav';
import finaleRevealWav from '$lib/assets/sounds/finale-reveal.wav';
import finaleStageOgg from '$lib/assets/sounds/finale-stage.ogg';
import pendingReviewClearedWav from '$lib/assets/sounds/pending-review-cleared.wav';
import scoreboardShownOgg from '$lib/assets/sounds/scoreboard-shown.ogg';
import stepClosedWav from '$lib/assets/sounds/step-closed.wav';
import stepOpenOgg from '$lib/assets/sounds/step-open.ogg';
import submissionReceivedOgg from '$lib/assets/sounds/submission-received.ogg';
import timerWarningWav from '$lib/assets/sounds/timer-warning.wav';
import winnerPodiumOgg from '$lib/assets/sounds/winner-podium.ogg';
import wrongWav from '$lib/assets/sounds/wrong.wav';

import type { SoundCue, SoundPlayer } from '$lib/sound-runtime.js';
import type { SoundSurface } from '$lib/sound-policy.js';

interface PlayerOptions {
	enabled?: boolean;
	masterVolume?: number;
	surface: SoundSurface;
}

const DEFAULT_SURFACE_ENABLED: Record<SoundSurface, boolean> = {
	'host-display': true,
	controller: false
};

const SAMPLE_BY_CUE: Record<SoundCue, string> = {
	answerReveal: answerRevealWav,
	buzzerArmed: buzzerArmedWav,
	buzz: buzzerOgg,
	correct: correctWav,
	finaleReveal: finaleRevealWav,
	finaleStage: finaleStageOgg,
	pendingReviewCleared: pendingReviewClearedWav,
	scoreboardShown: scoreboardShownOgg,
	stepClosed: stepClosedWav,
	stepOpen: stepOpenOgg,
	submissionReceived: submissionReceivedOgg,
	timerWarning: timerWarningWav,
	winnerPodium: winnerPodiumOgg,
	wrong: wrongWav
};

export function createBrowserSoundPlayer({
	surface,
	enabled = DEFAULT_SURFACE_ENABLED[surface],
	masterVolume = 0.75
}: PlayerOptions): SoundPlayer {
	const canPlay = browser && enabled;
	const sampleCache = new Map<string, HTMLAudioElement>();

	function baseSample(src: string): HTMLAudioElement {
		const existing = sampleCache.get(src);
		if (existing) {
			return existing;
		}
		const audio = new Audio(src);
		audio.preload = 'auto';
		sampleCache.set(src, audio);
		return audio;
	}

	function playSample(src: string) {
		const sample = baseSample(src);
		const next = sample.cloneNode() as HTMLAudioElement;
		next.volume = masterVolume;
		void next.play().catch(() => {});
	}

	return {
		play(cue) {
			if (!canPlay) {
				return;
			}
			playSample(SAMPLE_BY_CUE[cue]);
		}
	};
}
