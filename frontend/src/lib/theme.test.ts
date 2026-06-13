import { describe, expect, it } from 'vitest';

import { definitionThemeStyle, normalizeDefinitionTheme } from '$lib/theme.js';

describe('definition theme helpers', () => {
	it('defaults missing definition theme to the party system palette', () => {
		expect(normalizeDefinitionTheme()).toEqual({
			mode: 'system',
			palette: 'party',
			background: undefined,
			surface: undefined,
			ink: undefined,
			primary: undefined,
			accent: undefined
		});
	});

	it('includes custom color overrides in scoped CSS variables', () => {
		const style = definitionThemeStyle({
			mode: 'light',
			palette: 'forest',
			background: '#123456',
			primary: '#abcdef',
			accent: '#fedcba'
		});

		expect(style).toContain('--party-bg-a:#123456');
		expect(style).toContain('--party-primary:#abcdef');
		expect(style).toContain('--party-accent:#fedcba');
	});

	it('resolves scoped system themes from the active document color mode', () => {
		document.documentElement.dataset.colorMode = 'light';

		const style = definitionThemeStyle({ mode: 'system', palette: 'party' });

		expect(style).toContain('--party-bg-a:#f8fff1');
		expect(style).toContain('--party-surface-strong:rgba(255, 255, 255, 0.92)');
		expect(style).toContain('--party-ink:#1f2937');
		delete document.documentElement.dataset.colorMode;
	});

	it('includes mode-aware semantic tokens in scoped CSS variables', () => {
		const lightStyle = definitionThemeStyle({ mode: 'light', palette: 'party' });
		const darkStyle = definitionThemeStyle({ mode: 'dark', palette: 'party' });

		expect(lightStyle).toContain('--party-soft-correct-bg:color-mix(in srgb, #22c55e');
		expect(lightStyle).toContain('--party-soft-correct-text:#052e16');
		expect(lightStyle).toContain('--party-soft-warm-bg:color-mix(in srgb, #f97316');
		expect(darkStyle).toContain('--party-soft-correct-bg:color-mix(in srgb, #14532d');
		expect(darkStyle).toContain('--party-soft-correct-text:#f0fdf4');
		expect(darkStyle).toContain('--party-soft-warm-bg:color-mix(in srgb, #7c2d12');
	});
});
