import { writable, get } from 'svelte/store';
import type { SoundSurface } from '$lib/sound-policy';
import type { AudioSettings } from './audio-settings';
import type { AudioDriver, AudioVoice } from './audio-driver';
import type { PresentationProfile } from './registry';

export function createPresentationAudio(
	driver: AudioDriver,
	surface: SoundSurface,
	initial: AudioSettings
) {
	const blocked = writable(true);
	let settings = initial;
	let profile: PresentationProfile | undefined;
	let variant = '';
	let identity = '';
	let outgoing: AudioVoice | undefined;
	const failed = new Set<string>();
	let active = false;
	let enabled = false;
	let disposed = false;
	let music: { src: string; voice: AudioVoice } | undefined;
	const effects = new Map<AudioVoice, boolean>();
	const seen = new Set<string>();
	function musicVolume() {
		music?.voice.volume(settings.musicVolume * ([...effects.values()].some(Boolean) ? 0.25 : 1));
	}
	function stopEffects() {
		for (const voice of [...effects.keys()]) voice.stop();
		effects.clear();
	}
	function stopAll() {
		outgoing?.stop();
		outgoing = undefined;
		music?.voice.stop();
		music = undefined;
		stopEffects();
	}
	function reconcile() {
		if (disposed) return;
		const variantMusic = profile?.variants?.[variant]?.music;
		const src =
			active && enabled && settings.musicEnabled && surface === 'host-display'
				? variantMusic !== undefined
					? variantMusic
					: profile?.audio?.music
				: undefined;
		if (music?.src !== src) {
			outgoing?.stop();
			outgoing = music?.voice;
			outgoing?.stop(0.35);
			music = undefined;
			if (src && !failed.has(src)) {
				const voice = driver.play(
					src,
					true,
					() => {
						if (music?.voice === voice) music = undefined;
					},
					() => {
						failed.add(src);
						blocked.set(true);
					}
				);
				music = { src, voice };
			}
		}
		musicVolume();
	}
	return {
		blocked,
		select(next: PresentationProfile | undefined, runId = '', nextVariant = '') {
			const key = `${next?.gameType ?? ''}:${runId}`;
			if (key !== identity || next !== profile) {
				stopAll();
				seen.clear();
				identity = key;
			}
			profile = next;
			variant = nextVariant;
			reconcile();
		},
		async activate() {
			if (disposed) return;
			const retry = get(blocked);
			if (retry) failed.clear();
			enabled = await driver.activate();
			if (disposed) return;
			blocked.set(!enabled);
			// Retry a failed loop explicitly, without replaying effects.
			if (enabled && retry) {
				music?.voice.stop();
				music = undefined;
				reconcile();
			}
		},
		setActive(value: boolean) {
			active = value;
			if (!active) stopEffects();
			reconcile();
		},
		updateSettings(next: AudioSettings) {
			settings = next;
			if (!settings.effectsEnabled) stopEffects();
			else for (const voice of effects.keys()) voice.volume(settings.effectsVolume);
			reconcile();
		},
		cue(name: string, key: string, personal = false, suppress = false) {
			if (seen.has(key) || disposed) return;
			seen.add(key);
			const asset = profile?.audio?.effects?.[name];
			if (
				suppress ||
				!active ||
				!enabled ||
				!settings.effectsEnabled ||
				!asset ||
				(surface === 'controller' && !personal)
			)
				return;
			if (effects.size >= 3) {
				const oldest = effects.keys().next().value;
				oldest?.stop();
				if (oldest) effects.delete(oldest);
			}
			const voice = driver.play(
				asset.src,
				false,
				() => {
					effects.delete(voice);
					musicVolume();
				},
				() => blocked.set(true)
			);
			effects.set(voice, Boolean(asset.prominent));
			voice.volume(settings.effectsVolume, 0);
			musicVolume();
		},
		get needsActivation() {
			return get(blocked);
		},
		dispose() {
			if (disposed) return;
			disposed = true;
			stopAll();
			seen.clear();
			driver.dispose();
		}
	};
}
