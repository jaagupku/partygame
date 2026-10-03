import { writable } from 'svelte/store';
import type { SoundSurface } from '$lib/sound-policy';
export type AudioSettings = {
	musicEnabled: boolean;
	effectsEnabled: boolean;
	musicVolume: number;
	effectsVolume: number;
};
export const audioDefaults = (surface: SoundSurface): AudioSettings => ({
	musicEnabled: surface === 'host-display',
	effectsEnabled: true,
	musicVolume: 0.25,
	effectsVolume: surface === 'host-display' ? 0.78 : 0.35
});
export function normalizeAudioSettings(
	value: Partial<AudioSettings>,
	surface: SoundSurface
): AudioSettings {
	const defaults = audioDefaults(surface);
	const volume = (v: unknown, fallback: number) =>
		typeof v === 'number' && Number.isFinite(v) ? Math.max(0, Math.min(1, v)) : fallback;
	return {
		musicEnabled:
			surface === 'host-display' &&
			(typeof value.musicEnabled === 'boolean' ? value.musicEnabled : defaults.musicEnabled),
		effectsEnabled:
			typeof value.effectsEnabled === 'boolean' ? value.effectsEnabled : defaults.effectsEnabled,
		musicVolume: volume(value.musicVolume, defaults.musicVolume),
		effectsVolume: volume(value.effectsVolume, defaults.effectsVolume)
	};
}
export function createAudioSettings(
	surface: SoundSurface,
	storage?: Pick<Storage, 'getItem' | 'setItem'>
) {
	const key = `partygame-presentation-audio-v1:${surface}`;
	let initial = audioDefaults(surface);
	try {
		initial = normalizeAudioSettings(JSON.parse(storage?.getItem(key) ?? '{}') ?? {}, surface);
	} catch {
		/* unavailable storage */
	}
	const store = writable(initial);
	return {
		subscribe: store.subscribe,
		update(patch: Partial<AudioSettings>) {
			store.update((current) => {
				const next = normalizeAudioSettings({ ...current, ...patch }, surface);
				try {
					storage?.setItem(key, JSON.stringify(next));
				} catch {
					/* private browsing */
				}
				return next;
			});
		}
	};
}
export function deviceAudioSettings(surface: SoundSurface) {
	let storage: Storage | undefined;
	try {
		storage = globalThis.localStorage;
	} catch {
		/* unavailable storage */
	}
	return createAudioSettings(surface, storage);
}
