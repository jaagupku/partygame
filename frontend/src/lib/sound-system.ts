import { createBrowserSoundPlayer } from '$lib/sound-player.js';
import { createSoundRuntime, type SoundSurface } from '$lib/sound-runtime.js';
import { getSoundSettingsStore } from '$lib/sound-settings.js';
import { get } from 'svelte/store';

export function createSoundSystem(surface: SoundSurface) {
	const settingsStore = getSoundSettingsStore(surface);
	const settings = get(settingsStore);
	return createSoundRuntime(
		createBrowserSoundPlayer({
			surface,
			enabled: settings.soundEnabled,
			masterVolume: settings.masterVolume
		}),
		{ surface }
	);
}
