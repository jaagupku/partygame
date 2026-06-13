import { browser } from '$app/environment';
import { writable } from 'svelte/store';

export const APP_COLOR_MODES = ['light', 'dark', 'system'] as const;
export type AppColorMode = (typeof APP_COLOR_MODES)[number];

export const DEFINITION_THEME_MODES = ['light', 'dark', 'system'] as const;
export type DefinitionThemeMode = (typeof DEFINITION_THEME_MODES)[number];

export type ThemePaletteId = 'party' | 'midnight' | 'candy' | 'forest';

export type DefinitionTheme = {
	mode?: DefinitionThemeMode;
	palette?: ThemePaletteId;
	background?: string | null;
	surface?: string | null;
	ink?: string | null;
	primary?: string | null;
	accent?: string | null;
};

type ResolvedPalette = {
	background: string;
	backgroundAlt: string;
	backgroundWarm: string;
	surface: string;
	surfaceStrong: string;
	border: string;
	ink: string;
	subtle: string;
	primary: string;
	primaryStrong: string;
	accent: string;
	accentStrong: string;
	danger: string;
	dangerStrong: string;
};

type ThemeMode = 'light' | 'dark';
type ThemeVariables = Record<string, string>;

export const DEFAULT_DEFINITION_THEME: Required<Pick<DefinitionTheme, 'mode' | 'palette'>> = {
	mode: 'system',
	palette: 'party'
};

export const THEME_PALETTES: Record<
	ThemePaletteId,
	{ label: string; light: ResolvedPalette; dark: ResolvedPalette }
> = {
	party: {
		label: 'Party',
		light: {
			background: '#f8fff1',
			backgroundAlt: '#ddf2ff',
			backgroundWarm: '#fff4db',
			surface: 'rgba(255, 255, 255, 0.78)',
			surfaceStrong: 'rgba(255, 255, 255, 0.92)',
			border: 'rgba(17, 24, 39, 0.12)',
			ink: '#1f2937',
			subtle: '#526078',
			primary: '#0ea5e9',
			primaryStrong: '#0284c7',
			accent: '#f97316',
			accentStrong: '#ea580c',
			danger: '#ef4444',
			dangerStrong: '#dc2626'
		},
		dark: {
			background: '#111827',
			backgroundAlt: '#0f172a',
			backgroundWarm: '#2a1f16',
			surface: 'rgba(15, 23, 42, 0.78)',
			surfaceStrong: 'rgba(30, 41, 59, 0.94)',
			border: 'rgba(226, 232, 240, 0.18)',
			ink: '#f8fafc',
			subtle: '#cbd5e1',
			primary: '#0ea5e9',
			primaryStrong: '#0369a1',
			accent: '#f97316',
			accentStrong: '#c2410c',
			danger: '#f87171',
			dangerStrong: '#ef4444'
		}
	},
	midnight: {
		label: 'Midnight',
		light: {
			background: '#eef6ff',
			backgroundAlt: '#e0e7ff',
			backgroundWarm: '#fef3c7',
			surface: 'rgba(255, 255, 255, 0.8)',
			surfaceStrong: 'rgba(255, 255, 255, 0.94)',
			border: 'rgba(30, 41, 59, 0.14)',
			ink: '#172033',
			subtle: '#52617a',
			primary: '#2563eb',
			primaryStrong: '#1d4ed8',
			accent: '#d946ef',
			accentStrong: '#c026d3',
			danger: '#ef4444',
			dangerStrong: '#dc2626'
		},
		dark: {
			background: '#020617',
			backgroundAlt: '#111827',
			backgroundWarm: '#251638',
			surface: 'rgba(15, 23, 42, 0.82)',
			surfaceStrong: 'rgba(30, 41, 59, 0.96)',
			border: 'rgba(191, 219, 254, 0.2)',
			ink: '#eff6ff',
			subtle: '#bfdbfe',
			primary: '#60a5fa',
			primaryStrong: '#3b82f6',
			accent: '#e879f9',
			accentStrong: '#d946ef',
			danger: '#fb7185',
			dangerStrong: '#f43f5e'
		}
	},
	candy: {
		label: 'Candy',
		light: {
			background: '#fff1f2',
			backgroundAlt: '#ecfeff',
			backgroundWarm: '#fef9c3',
			surface: 'rgba(255, 255, 255, 0.82)',
			surfaceStrong: 'rgba(255, 255, 255, 0.95)',
			border: 'rgba(136, 19, 55, 0.14)',
			ink: '#3b1722',
			subtle: '#7f5361',
			primary: '#e11d48',
			primaryStrong: '#be123c',
			accent: '#06b6d4',
			accentStrong: '#0891b2',
			danger: '#dc2626',
			dangerStrong: '#b91c1c'
		},
		dark: {
			background: '#2a1020',
			backgroundAlt: '#0f2730',
			backgroundWarm: '#33220c',
			surface: 'rgba(62, 24, 45, 0.8)',
			surfaceStrong: 'rgba(76, 29, 56, 0.95)',
			border: 'rgba(251, 207, 232, 0.2)',
			ink: '#fff7fb',
			subtle: '#f9a8d4',
			primary: '#fb7185',
			primaryStrong: '#f43f5e',
			accent: '#22d3ee',
			accentStrong: '#06b6d4',
			danger: '#fca5a5',
			dangerStrong: '#f87171'
		}
	},
	forest: {
		label: 'Forest',
		light: {
			background: '#f0fdf4',
			backgroundAlt: '#dcfce7',
			backgroundWarm: '#fef3c7',
			surface: 'rgba(255, 255, 255, 0.8)',
			surfaceStrong: 'rgba(255, 255, 255, 0.94)',
			border: 'rgba(20, 83, 45, 0.14)',
			ink: '#14331f',
			subtle: '#4b7057',
			primary: '#16a34a',
			primaryStrong: '#15803d',
			accent: '#ca8a04',
			accentStrong: '#a16207',
			danger: '#dc2626',
			dangerStrong: '#b91c1c'
		},
		dark: {
			background: '#052e16',
			backgroundAlt: '#064e3b',
			backgroundWarm: '#29220e',
			surface: 'rgba(20, 83, 45, 0.78)',
			surfaceStrong: 'rgba(21, 128, 61, 0.9)',
			border: 'rgba(187, 247, 208, 0.2)',
			ink: '#f0fdf4',
			subtle: '#bbf7d0',
			primary: '#4ade80',
			primaryStrong: '#22c55e',
			accent: '#facc15',
			accentStrong: '#eab308',
			danger: '#f87171',
			dangerStrong: '#ef4444'
		}
	}
};

const APP_THEME_STORAGE_KEY = 'partyGameColorMode';

function getSystemMode(): 'light' | 'dark' {
	if (!browser || !window.matchMedia) {
		return 'light';
	}
	return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function isColorMode(value: unknown): value is AppColorMode {
	return typeof value === 'string' && APP_COLOR_MODES.includes(value as AppColorMode);
}

function readInitialMode(): AppColorMode {
	if (!browser) {
		return 'system';
	}
	const stored = localStorage.getItem(APP_THEME_STORAGE_KEY);
	return isColorMode(stored) ? stored : 'system';
}

export const appColorMode = writable<AppColorMode>(readInitialMode());

export function resolveThemeMode(
	mode: DefinitionThemeMode | AppColorMode | undefined
): 'light' | 'dark' {
	return mode === 'light' || mode === 'dark' ? mode : getSystemMode();
}

function resolveScopedThemeMode(mode: DefinitionThemeMode | undefined): 'light' | 'dark' {
	if (mode === 'light' || mode === 'dark') {
		return mode;
	}
	if (browser) {
		const colorMode = document.documentElement.dataset.colorMode;
		if (colorMode === 'light' || colorMode === 'dark') {
			return colorMode;
		}
	}
	return getSystemMode();
}

function semanticThemeVariables(palette: ResolvedPalette, mode: ThemeMode): ThemeVariables {
	const variables: ThemeVariables = {
		'--party-success': '#16a34a',
		'--party-success-strong': '#047857',
		'--party-warm': '#7c2d12',
		'--party-warm-strong': '#9a3412',
		'--party-warning': '#92400e',
		'--party-warning-strong': '#b45309',
		'--party-critical': '#7f1d1d',
		'--party-critical-strong': '#991b1b',
		'--party-soft-surface': `color-mix(in srgb, ${palette.surfaceStrong}, ${palette.backgroundAlt} 18%)`,
		'--party-raised-surface': `color-mix(in srgb, ${palette.surfaceStrong}, white 5%)`,
		'--party-muted-control': `color-mix(in srgb, ${palette.surfaceStrong}, ${palette.ink} 10%)`,
		'--party-soft-primary-border': `color-mix(in srgb, ${palette.primary}, ${palette.border} 55%)`,
		'--party-soft-primary-bg': `color-mix(in srgb, ${palette.primary}, ${palette.surfaceStrong} 84%)`,
		'--party-soft-primary-text': `color-mix(in srgb, ${palette.primaryStrong}, ${palette.ink} 22%)`,
		'--party-soft-accent-border': `color-mix(in srgb, ${palette.accent}, ${palette.border} 55%)`,
		'--party-soft-accent-bg': `color-mix(in srgb, ${palette.accent}, ${palette.surfaceStrong} 84%)`,
		'--party-soft-accent-text': `color-mix(in srgb, ${palette.accentStrong}, ${palette.ink} 22%)`,
		'--party-soft-danger-border': `color-mix(in srgb, ${palette.danger}, ${palette.border} 55%)`,
		'--party-soft-danger-bg': `color-mix(in srgb, ${palette.danger}, ${palette.surfaceStrong} 84%)`,
		'--party-soft-danger-text': `color-mix(in srgb, ${palette.dangerStrong}, ${palette.ink} 22%)`,
		'--party-soft-success-border': `color-mix(in srgb, #16a34a, ${palette.border} 38%)`,
		'--party-soft-success-bg': `color-mix(in srgb, #16a34a, ${palette.surfaceStrong} 78%)`,
		'--party-soft-success-text': palette.ink,
		'--party-soft-success-label': `color-mix(in srgb, #047857, ${palette.ink} 24%)`,
		'--party-soft-correct-border': `color-mix(in srgb, #22c55e, ${palette.border} 32%)`,
		'--party-soft-correct-bg': `color-mix(in srgb, #22c55e, ${palette.surfaceStrong} 64%)`,
		'--party-soft-correct-text': '#052e16',
		'--party-soft-correct-label': '#047857',
		'--party-soft-warm-border': `color-mix(in srgb, ${palette.accent}, ${palette.border} 35%)`,
		'--party-soft-warm-bg': `color-mix(in srgb, ${palette.accent}, ${palette.surfaceStrong} 64%)`,
		'--party-soft-warm-text': '#431407',
		'--party-soft-warm-label': '#c2410c',
		'--party-soft-warning-border': `color-mix(in srgb, #f59e0b, ${palette.border} 28%)`,
		'--party-soft-warning-bg': `color-mix(in srgb, #f59e0b, ${palette.surfaceStrong} 62%)`,
		'--party-soft-warning-text': '#451a03',
		'--party-soft-warning-label': '#b45309',
		'--party-soft-critical-border': `color-mix(in srgb, ${palette.danger}, ${palette.border} 25%)`,
		'--party-soft-critical-bg': `color-mix(in srgb, ${palette.danger}, ${palette.surfaceStrong} 64%)`,
		'--party-soft-critical-text': '#450a0a',
		'--party-soft-critical-label': '#b91c1c'
	};

	if (mode === 'dark') {
		return {
			...variables,
			'--party-soft-correct-bg': `color-mix(in srgb, #14532d, ${palette.surfaceStrong} 34%)`,
			'--party-soft-correct-text': '#f0fdf4',
			'--party-soft-correct-label': '#bbf7d0',
			'--party-soft-warm-bg': `color-mix(in srgb, #7c2d12, ${palette.surfaceStrong} 34%)`,
			'--party-soft-warm-text': palette.ink,
			'--party-soft-warm-label': '#fed7aa',
			'--party-soft-warning-bg': `color-mix(in srgb, #92400e, ${palette.surfaceStrong} 32%)`,
			'--party-soft-warning-text': palette.ink,
			'--party-soft-warning-label': '#fed7aa',
			'--party-soft-critical-bg': `color-mix(in srgb, #7f1d1d, ${palette.surfaceStrong} 30%)`,
			'--party-soft-critical-text': palette.ink,
			'--party-soft-critical-label': '#fecaca'
		};
	}

	return variables;
}

function paletteThemeVariables(palette: ResolvedPalette, mode: ThemeMode): ThemeVariables {
	return {
		'--party-bg-a': palette.background,
		'--party-bg-b': palette.backgroundAlt,
		'--party-bg-c': palette.backgroundWarm,
		'--party-surface': palette.surface,
		'--party-surface-strong': palette.surfaceStrong,
		'--party-border': palette.border,
		'--party-ink': palette.ink,
		'--party-subtle': palette.subtle,
		'--party-primary': palette.primary,
		'--party-primary-strong': palette.primaryStrong,
		'--party-accent': palette.accent,
		'--party-accent-strong': palette.accentStrong,
		'--party-danger': palette.danger,
		'--party-danger-strong': palette.dangerStrong,
		...semanticThemeVariables(palette, mode)
	};
}

function applyPaletteToElement(element: HTMLElement, palette: ResolvedPalette, mode: ThemeMode) {
	for (const [property, value] of Object.entries(paletteThemeVariables(palette, mode))) {
		element.style.setProperty(property, value);
	}
}

export function normalizeDefinitionTheme(theme?: DefinitionTheme | null): DefinitionTheme {
	return {
		mode: theme?.mode ?? DEFAULT_DEFINITION_THEME.mode,
		palette: theme?.palette ?? DEFAULT_DEFINITION_THEME.palette,
		background: theme?.background,
		surface: theme?.surface,
		ink: theme?.ink,
		primary: theme?.primary,
		accent: theme?.accent
	};
}

export function definitionThemeStyle(theme?: DefinitionTheme | null): string {
	const normalized = normalizeDefinitionTheme(theme);
	const mode = resolveScopedThemeMode(normalized.mode);
	const palette = THEME_PALETTES[normalized.palette ?? 'party'] ?? THEME_PALETTES.party;
	const colors: ResolvedPalette = {
		...palette[mode],
		background: normalized.background ?? palette[mode].background,
		backgroundAlt: normalized.background ?? palette[mode].backgroundAlt,
		surface: normalized.surface ?? palette[mode].surface,
		surfaceStrong: normalized.surface ?? palette[mode].surfaceStrong,
		ink: normalized.ink ?? palette[mode].ink,
		subtle: normalized.ink ?? palette[mode].subtle,
		primary: normalized.primary ?? palette[mode].primary,
		primaryStrong: normalized.primary ?? palette[mode].primaryStrong,
		accent: normalized.accent ?? palette[mode].accent,
		accentStrong: normalized.accent ?? palette[mode].accentStrong
	};
	return Object.entries(paletteThemeVariables(colors, mode))
		.map(([property, value]) => `${property}:${value}`)
		.join(';');
}

function applyAppMode(mode: AppColorMode) {
	if (!browser) {
		return;
	}
	const resolvedMode = resolveThemeMode(mode);
	const root = document.documentElement;
	root.dataset.colorMode = resolvedMode;
	root.dataset.themePreference = mode;
	applyPaletteToElement(root, THEME_PALETTES.party[resolvedMode], resolvedMode);
	localStorage.setItem(APP_THEME_STORAGE_KEY, mode);
}

if (browser) {
	appColorMode.subscribe(applyAppMode);
	window.matchMedia?.('(prefers-color-scheme: dark)').addEventListener('change', () => {
		appColorMode.update((mode) => mode);
	});
}
