import { get } from 'svelte/store';
import { appColorMode, paletteThemeVariables, resolveThemeMode, THEME_PALETTES } from '$lib/theme';
import { presentationRevision, resolvePresentation } from './registry';

export type ScopeSelection = { gameType?: string | null; variant?: string; screen?: boolean };
let restoreScreen: (() => void) | undefined;
const defaults = {
	'--presentation-font': "'Nunito', system-ui, sans-serif",
	'--presentation-heading-font': "'Baloo 2', system-ui, sans-serif",
	'--presentation-card-radius': '1.5rem',
	'--presentation-border-width': '1px',
	'--presentation-card-shadow': '0 12px 30px rgb(15 23 42 / 0.08)',
	'--presentation-illustration-radius': '1rem',
	'--presentation-transition': '180ms ease'
};
function presentationColorScheme(selection: ScopeSelection) {
	const profile = resolvePresentation(selection.gameType);
	const variant = selection.variant
		? profile?.variants?.[selection.variant]?.appearance
		: undefined;
	return profile
		? (variant?.colorScheme ?? profile.appearance.colorScheme ?? 'light')
		: resolveThemeMode(get(appColorMode));
}
export function presentationVariables(selection: ScopeSelection) {
	const profile = resolvePresentation(selection.gameType);
	const appearance = profile?.appearance;
	const variant = selection.variant
		? profile?.variants?.[selection.variant]?.appearance
		: undefined;
	const mode = presentationColorScheme(selection);
	return {
		...paletteThemeVariables(
			{ ...THEME_PALETTES.party[mode], ...appearance?.palette, ...variant?.palette },
			mode
		),
		...defaults,
		...appearance?.tokens,
		...variant?.tokens
	};
}
/** Local scopes never modify ancestors. Screen scopes own only body overrides and restore them. */
export function presentationScope(node: HTMLElement, selection: ScopeSelection = {}) {
	let restore = () => {};
	function apply() {
		restore();
		if (selection.screen) restoreScreen?.();
		const target = selection.screen ? document.body : node;
		const profile = resolvePresentation(selection.gameType);
		// A nested neutral/quiz preview must reset an enclosing game's variables.
		const nested = !selection.screen && Boolean(node.parentElement?.closest('[data-presentation]'));
		if (!profile && !nested) return;
		const oldName = target.getAttribute('data-presentation');
		const oldVariant = target.getAttribute('data-presentation-variant');
		const oldMode = target.style.colorScheme;
		const variables = presentationVariables(selection);
		const previous = Object.keys(variables).map((key) => [key, target.style.getPropertyValue(key)]);
		for (const [key, value] of Object.entries(variables)) target.style.setProperty(key, value);
		target.dataset.presentation = profile?.gameType ?? 'neutral';
		target.dataset.presentationVariant = selection.variant ?? 'default';
		target.style.colorScheme = presentationColorScheme(selection);
		restore = () => {
			for (const [key, value] of previous)
				value ? target.style.setProperty(key, value) : target.style.removeProperty(key);
			for (const [key, value] of [
				['data-presentation', oldName],
				['data-presentation-variant', oldVariant]
			]) {
				if (value === null) target.removeAttribute(key!);
				else target.setAttribute(key!, value!);
			}
			target.style.colorScheme = oldMode;
			if (restoreScreen === restore) restoreScreen = undefined;
			restore = () => {};
		};
		if (selection.screen) restoreScreen = restore;
	}
	const unsubscribeMode = appColorMode.subscribe(apply);
	const unsubscribeRegistry = presentationRevision.subscribe(apply);
	const systemMode = window.matchMedia?.('(prefers-color-scheme: dark)');
	systemMode?.addEventListener('change', apply);
	return {
		update(next: ScopeSelection) {
			selection = next;
			apply();
		},
		destroy() {
			unsubscribeMode();
			unsubscribeRegistry();
			systemMode?.removeEventListener('change', apply);
			restore();
		}
	};
}
/** Copies the nearest local scope to a viewport portal, including future theme/variant changes. */
export function presentationPortal(node: HTMLElement) {
	const ancestors: HTMLElement[] = [];
	for (let parent = node.parentElement; parent; parent = parent.parentElement)
		ancestors.push(parent);
	const wrapper = document.createElement('div');
	wrapper.style.display = 'contents';
	function sync() {
		const owner = ancestors.find((element) => element.hasAttribute('data-presentation'));
		wrapper.style.cssText = owner ? `${owner.style.cssText};display:contents` : 'display:contents';
		for (const key of ['data-presentation', 'data-presentation-variant']) {
			const value = owner?.getAttribute(key);
			if (value == null) wrapper.removeAttribute(key);
			else wrapper.setAttribute(key, value);
		}
	}
	sync();
	const observer = new MutationObserver(sync);
	for (const owner of ancestors)
		observer.observe(owner, {
			attributes: true,
			attributeFilter: ['style', 'data-presentation', 'data-presentation-variant']
		});
	document.body.append(wrapper);
	wrapper.append(node);
	return {
		destroy() {
			observer.disconnect();
			wrapper.remove();
		}
	};
}
