import { describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';
import { createAudioSettings, audioDefaults } from './audio-settings';
import { createPresentationAudio } from './audio-engine';
import type { AudioVoice } from './audio-driver';
import type { PresentationProfile } from './registry';
const profile: PresentationProfile = {
	gameType: 'price_guessing',
	appearance: { palette: {} },
	audio: { music: 'lobby.wav', effects: { reveal: { src: 'reveal.wav', prominent: true } } },
	variants: { finale: { music: 'finale.wav' } }
};
function fixture(surface: 'host-display' | 'controller' = 'host-display') {
	const voices: (AudioVoice & { src: string; end: () => void; fail: () => void })[] = [];
	const driver = {
		activate: vi.fn(async () => true),
		dispose: vi.fn(),
		play: vi.fn((src: string, loop: boolean, end: () => void, fail: () => void) => {
			const voice = { src, volume: vi.fn(), stop: vi.fn(end), end, fail };
			voices.push(voice);
			return voice;
		})
	};
	const audio = createPresentationAudio(driver, surface, audioDefaults(surface));
	audio.select(profile, 'r1');
	audio.setActive(true);
	return { audio, driver, voices };
}
describe('mode audio', () => {
	it('defaults sound on and persists independent bounded settings', () => {
		localStorage.clear();
		const settings = createAudioSettings('host-display', localStorage);
		expect(get(settings)).toMatchObject({
			musicEnabled: true,
			effectsEnabled: true,
			musicVolume: 0.25,
			effectsVolume: 0.78
		});
		settings.update({ musicEnabled: false, musicVolume: 2, effectsVolume: 0.4 });
		expect(get(createAudioSettings('host-display', localStorage))).toMatchObject({
			musicEnabled: false,
			musicVolume: 1,
			effectsVolume: 0.4
		});
		const phone = createAudioSettings('controller', localStorage);
		phone.update({ musicEnabled: true });
		expect(get(phone)).toMatchObject({
			musicEnabled: false,
			effectsEnabled: true,
			effectsVolume: 0.35
		});
		phone.update({ effectsEnabled: false });
		expect(get(createAudioSettings('controller', localStorage)).effectsEnabled).toBe(false);
	});
	it('activates once, deduplicates loops, transitions variants, ducks and updates live channels', async () => {
		const { audio, driver, voices } = fixture();
		expect(driver.play).not.toHaveBeenCalled();
		await audio.activate();
		expect(voices).toHaveLength(1);
		audio.select(profile, 'r1');
		expect(voices).toHaveLength(1);
		audio.cue('reveal', 'step1');
		expect(voices[0].volume).toHaveBeenLastCalledWith(0.25 * 0.25);
		audio.cue('reveal', 'step1');
		expect(voices).toHaveLength(2);
		audio.updateSettings({
			...audioDefaults('host-display'),
			musicVolume: 0.5,
			effectsVolume: 0.2
		});
		expect(voices[1].volume).toHaveBeenLastCalledWith(0.2);
		voices[1].end();
		expect(voices[0].volume).toHaveBeenLastCalledWith(0.5);
		audio.select(profile, 'r1', 'finale');
		expect(voices[0].stop).toHaveBeenCalledWith(0.35);
		expect(voices.at(-1)?.src).toBe('finale.wav');
		audio.dispose();
		expect(driver.dispose).toHaveBeenCalledTimes(1);
	});
	it('bounds effects, suppresses missed cues, resets on replay and stops inactive playback', async () => {
		const { audio, voices } = fixture();
		await audio.activate();
		for (let i = 0; i < 5; i++) audio.cue('reveal', `cue${i}`);
		expect(voices[1].stop).toHaveBeenCalled();
		expect(voices[2].stop).toHaveBeenCalled();
		audio.setActive(false);
		audio.cue('reveal', 'missed');
		expect(voices[0].stop).toHaveBeenCalledWith(0.35);
		audio.setActive(true);
		const count = voices.length;
		audio.cue('reveal', 'missed');
		expect(voices).toHaveLength(count);
		audio.select(profile, 'r2');
		audio.cue('reveal', 'missed');
		expect(voices.length).toBeGreaterThan(count);
		audio.dispose();
		const final = voices.length;
		await audio.activate();
		audio.cue('reveal', 'late');
		expect(voices).toHaveLength(final);
	});
	it('handles rejected activation and asset failure with an explicit retry', async () => {
		const { audio, driver, voices } = fixture();
		driver.activate.mockResolvedValueOnce(false);
		await audio.activate();
		expect(audio.needsActivation).toBe(true);
		expect(voices).toHaveLength(0);
		await audio.activate();
		voices[0].fail();
		expect(audio.needsActivation).toBe(true);
		await audio.activate();
		expect(audio.needsActivation).toBe(false);
		audio.dispose();
	});
	it('phones default to personal effects, respect muting, and never play music or shared cues', async () => {
		const { audio, voices } = fixture('controller');
		await audio.activate();
		audio.cue('reveal', 'one');
		expect(voices).toHaveLength(0);
		audio.updateSettings({
			...audioDefaults('controller'),
			effectsEnabled: true,
			musicEnabled: true
		});
		audio.cue('reveal', 'two');
		expect(voices).toHaveLength(0);
		audio.cue('reveal', 'three', true);
		expect(voices).toHaveLength(1);
		audio.updateSettings({ ...audioDefaults('controller'), effectsEnabled: false });
		audio.cue('reveal', 'muted', true);
		expect(voices).toHaveLength(1);
		audio.dispose();
	});
});
