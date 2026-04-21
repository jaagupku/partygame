import { get } from 'svelte/store';

import { createSoundDetector, type RuntimeEvent, type RuntimeLikeState, type SoundCue } from '$lib/sound-detector.js';
import { createSoundPolicy, type SoundSurface } from '$lib/sound-policy.js';
import { getSoundSettingsStore } from '$lib/sound-settings.js';

export type { SoundCue } from '$lib/sound-detector.js';
export type { SoundSurface } from '$lib/sound-policy.js';

export interface SoundPlayer {
	play(cue: SoundCue): void;
}

interface SyncOptions {
	baseline?: boolean;
	suppressCues?: boolean;
}

interface RuntimeOptions {
	surface: SoundSurface;
	timerWarningSeconds?: number;
}

export function createSoundRuntime(
	player: SoundPlayer,
	{ surface, timerWarningSeconds = 3 }: RuntimeOptions
) {
	const detector = createSoundDetector({ timerWarningSeconds });
	const settingsStore = getSoundSettingsStore(surface);
	let stateGetter: (() => RuntimeLikeState | null | undefined) | null = null;
	let timerIntervalId: ReturnType<typeof setInterval> | null = null;

	function playCues(cues: SoundCue[]) {
		const policy = createSoundPolicy(surface, get(settingsStore));
		for (const cue of cues) {
			if (policy.shouldPlay(cue)) {
				player.play(cue);
			}
		}
	}

	function syncState(nextStateLike?: RuntimeLikeState | null, options: SyncOptions = {}) {
		playCues(detector.syncState(nextStateLike, options));
	}

	function handleEvent(event: RuntimeEvent, stateLike?: RuntimeLikeState | null) {
		playCues(detector.handleEvent(event, stateLike));
	}

	function tick(nowMs = Date.now(), suppressCues = false) {
		const state = stateGetter ? stateGetter() : null;
		playCues(detector.tick(state, nowMs, suppressCues));
	}

	function start(getState: () => RuntimeLikeState | null | undefined) {
		stateGetter = getState;
		if (timerIntervalId !== null) {
			clearInterval(timerIntervalId);
		}
		timerIntervalId = setInterval(() => {
			tick();
		}, 250);
	}

	function dispose() {
		if (timerIntervalId !== null) {
			clearInterval(timerIntervalId);
			timerIntervalId = null;
		}
		stateGetter = null;
	}

	return {
		syncState,
		handleEvent,
		tick,
		start,
		dispose
	};
}
