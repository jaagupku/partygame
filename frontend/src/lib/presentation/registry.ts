import type { Component } from 'svelte';
import { pricePresentation } from './price/profile';
import { caloriePresentation } from './calorie/profile';
import { drawingPresentation } from './drawing/profile';
import { writable } from 'svelte/store';
import type { ResolvedPalette } from '$lib/theme';

export type PresentationGame = 'price_guessing' | 'calorie_guessing' | 'drawing_mashup';
export type PresentationState = HostGameState | ControllerState;
export type PresentationCue = { name: string; key: string; audience?: 'shared' | 'personal' };
export type Appearance = {
	/** One authored palette, independent of app and system theme preferences. */
	palette: Partial<ResolvedPalette>;
	/** Fixed semantic/native-control scheme chosen by the designer; defaults to light. */
	colorScheme?: 'light' | 'dark';
	/** CSS custom properties, e.g. --presentation-font, --presentation-card-radius. */
	tokens?: Record<`--${string}`, string>;
	Decoration?: Component<{ variant: string; surface: DecorationSurface }>;
};
/** Full display screens, phone controllers, or individual homepage/setup previews. */
export type DecorationSurface = 'screen' | 'controller' | 'preview';
export type AudioAsset = { src: string; prominent?: boolean };
export type PresentationProfile = {
	gameType: PresentationGame;
	appearance: Appearance;
	variants?: Record<string, { appearance?: Partial<Appearance>; music?: string | null }>;
	audio?: {
		music?: string;
		effects?: Record<string, AudioAsset>;
	};
	/** Pure projection of public runtime state. Keys identify milestones, not renders. */
	adapt?: (state: PresentationState) => { variant?: string; cues?: PresentationCue[] };
};

const profiles = new Map<string, PresentationProfile>();
export const presentationRevision = writable(0);
/** `replace` lets tests swap a registered profile; the returned cleanup restores it. */
export function registerPresentation(profile: PresentationProfile, { replace = false } = {}) {
	if (!['price_guessing', 'calorie_guessing', 'drawing_mashup'].includes(profile.gameType)) {
		throw new Error('Only standalone game presentations can be registered');
	}
	const previous = profiles.get(profile.gameType);
	if (previous && !replace) throw new Error(`Presentation already registered: ${profile.gameType}`);
	profiles.set(profile.gameType, profile);
	presentationRevision.update((n) => n + 1);
	return () => {
		if (profiles.get(profile.gameType) !== profile) return;
		if (previous) profiles.set(profile.gameType, previous);
		else profiles.delete(profile.gameType);
		presentationRevision.update((n) => n + 1);
	};
}
export function resolvePresentation(gameType?: string | null) {
	return gameType ? profiles.get(gameType) : undefined;
}
export function presentationIdentity(state: PresentationState) {
	return 'gameState' in state
		? { gameType: state.gameType, runId: state.runId }
		: { gameType: state.game_type, runId: state.run_id ?? state.id };
}
export function selectPresentation(state: PresentationState) {
	const identity = presentationIdentity(state);
	const profile = resolvePresentation(identity.gameType);
	return { ...identity, profile, ...profile?.adapt?.(state) };
}
// Profiles use type-only registry imports to avoid side-effect cycles.
registerPresentation(pricePresentation);
registerPresentation(caloriePresentation);
registerPresentation(drawingPresentation);
