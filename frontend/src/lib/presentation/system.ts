import { get, writable } from 'svelte/store';
import { createSoundSystem } from '$lib/sound-system';
import { createSoundDetector, type RuntimeEvent } from '$lib/sound-detector';
import type { SoundSurface } from '$lib/sound-policy';
import { createBrowserAudioDriver } from './audio-driver';
import { deviceAudioSettings } from './audio-settings';
import { createPresentationAudio } from './audio-engine';
import { selectPresentation, type PresentationState } from './registry';

type SyncOptions = { baseline?: boolean; suppressCues?: boolean };
export function createPresentationSystem(surface: SoundSurface) {
	const settings = deviceAudioSettings(surface);
	const blocked = writable(true);
	let legacy: ReturnType<typeof createSoundSystem> | undefined;
	let audio: ReturnType<typeof createPresentationAudio> | undefined;
	let unsubscribeBlocked: (() => void) | undefined;
	let detector = createSoundDetector();
	let state: PresentationState | undefined;
	let getState: (() => PresentationState) | undefined;
	let timer: ReturnType<typeof setInterval> | undefined;
	let connected = false;
	let recovering = true;
	let hidden = typeof document !== 'undefined' && document.hidden;
	let disposed = false;
	let identity = '';
	let accepted = false;
	const unsubscribeSettings = settings.subscribe((value) => audio?.updateSettings(value));
	function isActive() {
		return (
			connected &&
			!hidden &&
			state &&
			('gameState' in state ? state.gameState : state.state) !== 'paused'
		);
	}
	function syncState(next: PresentationState, options: SyncOptions = {}) {
		if (disposed) return;
		state = next;
		const selection = selectPresentation(next);
		const key = `${selection.gameType}:${selection.runId}`;
		const changed = identity !== key;
		const baseline = Boolean(options.baseline || options.suppressCues || recovering || changed);
		const suppress = Boolean(
			baseline || options.suppressCues || !isActive() || next.reviewingHistory
		);
		if (changed) {
			detector = createSoundDetector();
			identity = key;
		}
		if (!selection.profile) {
			audio?.dispose();
			audio = undefined;
			unsubscribeBlocked?.();
			unsubscribeBlocked = undefined;
			if (!legacy) {
				legacy = createSoundSystem(surface);
				if (getState) legacy.start(getState);
			}
			legacy.syncState(next, options);
			return;
		}
		legacy?.dispose();
		legacy = undefined;
		if (!audio) {
			audio = createPresentationAudio(createBrowserAudioDriver(), surface, get(settings));
			unsubscribeBlocked = audio.blocked.subscribe(blocked.set);
			void audio.activate();
		}
		audio.select(selection.profile, selection.runId, selection.variant);
		audio.setActive(Boolean(isActive()));
		const cues = detector.syncState(next, { baseline, suppressCues: suppress });
		for (const cue of cues) {
			if (surface === 'host-display')
				audio.cue(
					cue,
					`${next.activeStep?.id}:${next.displayPhase}:${next.endGame?.sequence_stage}:${cue}`,
					false,
					suppress
				);
		}
		// Aggregate submission counts are never personal confirmations. Drawing autosaves are silent.
		const ownAccepted =
			'gameState' in next && next.activeStep?.input_kind !== 'drawing' && next.hasSubmitted;
		if (surface === 'controller' && ownAccepted && !accepted)
			audio.cue('submissionReceived', `${next.activeStep?.id}:accepted`, true, suppress);
		accepted = Boolean(ownAccepted);
		for (const cue of selection.cues ?? [])
			audio.cue(cue.name, `adapter:${cue.key}`, cue.audience === 'personal', suppress);
		if (connected) recovering = false;
	}
	function handleEvent(event: RuntimeEvent, next?: PresentationState) {
		if (disposed || !next) return;
		if (!selectPresentation(next).profile) {
			legacy?.handleEvent(event, next);
			return;
		}
		// Snapshots/patches are handled by syncState; event cues only on an established live run.
		if (surface !== 'host-display' || recovering || !isActive() || next.reviewingHistory) return;
		for (const cue of detector.handleEvent(event, next)) {
			const batch =
				'batch_id' in event
					? String(event.batch_id)
					: `${event.type_}:${'player_id' in event ? event.player_id : ''}:${next.activeStep?.timer.started_at ?? ''}:${next.displayPhase}`;
			audio?.cue(cue, `event:${next.activeStep?.id}:${batch}:${cue}`);
		}
	}
	function visibility() {
		hidden = document.hidden;
		if (state && selectPresentation(state).profile) {
			if (!hidden) void audio?.activate();
			syncState(state, { baseline: true });
		}
	}
	function activateOnInteraction() {
		if (audio?.needsActivation) void audio.activate();
	}
	return {
		settings,
		blocked,
		handleCue(name: string, milestoneKey: string, personal = false) {
			audio?.cue(name, `explicit:${milestoneKey}`, personal, recovering || !isActive());
		},
		syncState,
		handleEvent,
		activate() {
			void audio?.activate();
		},
		setConnected(value: boolean) {
			connected = value;
			recovering = true;
			if (!value) audio?.setActive(false);
		},
		start(read: () => PresentationState) {
			getState = read;
			legacy?.start(read);
			if (timer) clearInterval(timer);
			document.addEventListener('visibilitychange', visibility);
			document.addEventListener('pointerup', activateOnInteraction);
			document.addEventListener('keydown', activateOnInteraction);
			timer = setInterval(() => {
				if (!getState) return;
				const next = getState();
				if (!selectPresentation(next).profile) {
					return;
				}
				const suppress = recovering || !isActive() || next.reviewingHistory;
				// Establish timer markers on recovery so missed warnings are never replayed.
				if (suppress) detector.syncState(next, { baseline: true });
				for (const cue of detector.tick(next, Date.now(), suppress)) {
					if (surface === 'host-display')
						audio?.cue(
							cue,
							`${next.activeStep?.id}:${cue}:${Math.ceil((next.activeStep?.timer.ends_at ?? 0) - Date.now() / 1000)}`
						);
				}
			}, 250);
		},
		dispose() {
			if (disposed) return;
			disposed = true;
			if (timer) clearInterval(timer);
			if (typeof document !== 'undefined') {
				document.removeEventListener('visibilitychange', visibility);
				document.removeEventListener('pointerup', activateOnInteraction);
				document.removeEventListener('keydown', activateOnInteraction);
			}
			getState = undefined;
			state = undefined;
			unsubscribeSettings();
			unsubscribeBlocked?.();
			audio?.dispose();
			legacy?.dispose();
		}
	};
}
export type PresentationSystem = ReturnType<typeof createPresentationSystem>;
