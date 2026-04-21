import { writable } from 'svelte/store';

import { DEFAULT_SOUND_SETTINGS, type SoundSettings, type SoundSurface } from '$lib/sound-policy.js';

const stores = new Map<SoundSurface, ReturnType<typeof writable<SoundSettings>>>();

export function getSoundSettingsStore(surface: SoundSurface) {
	const existing = stores.get(surface);
	if (existing) {
		return existing;
	}
	const store = writable<SoundSettings>({ ...DEFAULT_SOUND_SETTINGS[surface] });
	stores.set(surface, store);
	return store;
}
