import { afterEach, describe, expect, it } from 'vitest';
import { appColorMode } from '$lib/theme';
import {
	registerPresentation,
	resolvePresentation,
	selectPresentation,
	type PresentationProfile
} from './registry';
import { presentationScope, presentationPortal } from './scope';
const cleanups: (() => void)[] = [];
const profile: PresentationProfile = {
	gameType: 'drawing_mashup',
	appearance: { palette: { primary: '#123456' } },
	variants: {
		receipt: { appearance: { palette: { primary: '#654321' }, colorScheme: 'dark' } }
	},
	adapt: () => ({ variant: 'receipt' })
};
afterEach(() => {
	cleanups.reverse().forEach((fn) => fn());
	cleanups.length = 0;
	document.body.innerHTML = '';
	appColorMode.set('system');
});
describe('presentation scopes', () => {
	it('leaves missing profiles and trivia untouched, resolves authoritative identities', () => {
		expect(resolvePresentation('trivia')).toBeUndefined();
		expect(resolvePresentation('unknown')).toBeUndefined();
		const node = document.createElement('div');
		node.style.setProperty('--party-primary', 'purple');
		const scope = presentationScope(node, { gameType: 'unknown' });
		cleanups.push(scope.destroy);
		expect(node.style.getPropertyValue('--party-primary')).toBe('purple');
		cleanups.push(registerPresentation(profile, { replace: true }));
		expect(
			selectPresentation({
				gameType: 'drawing_mashup',
				runId: 'r2',
				gameState: 'running'
			} as ControllerState)
		).toMatchObject({ profile, runId: 'r2', variant: 'receipt' });
		expect(
			selectPresentation({ game_type: 'trivia', run_id: 'r3' } as HostGameState).profile
		).toBeUndefined();
	});
	it('rejects duplicates unless a test replaces a profile, then restores the original', () => {
		const original = resolvePresentation('price_guessing');
		const fake = { ...profile, gameType: 'price_guessing' as const };
		expect(() => registerPresentation(fake)).toThrow('already registered');
		const restore = registerPresentation(fake, { replace: true });
		expect(resolvePresentation('price_guessing')).toBe(fake);
		restore();
		expect(resolvePresentation('price_guessing')).toBe(original);
	});
	it('keeps authored screen and variant styles fixed while neutral scopes follow the app preference', async () => {
		cleanups.push(registerPresentation(profile, { replace: true }));
		appColorMode.set('light');
		const marker = document.createElement('div');
		const card = document.createElement('div');
		document.body.append(marker, card);
		const screen = presentationScope(marker, { gameType: 'drawing_mashup', screen: true });
		cleanups.push(screen.destroy);
		expect(document.body.style.getPropertyValue('--party-primary')).toBe('#123456');
		expect(document.body.style.getPropertyValue('--party-soft-primary-bg')).toContain('#123456');
		const nested = presentationScope(card, { gameType: 'drawing_mashup', variant: 'receipt' });
		cleanups.push(nested.destroy);
		const control = document.createElement('button');
		card.append(control);
		const portal = presentationPortal(control);
		cleanups.push(portal.destroy);
		expect(control.parentElement!.style.getPropertyValue('--party-primary')).toBe('#654321');
		const screenStyle = document.body.style.cssText;
		const portalStyle = control.parentElement!.style.cssText;
		for (const mode of ['dark', 'system', 'light'] as const) {
			appColorMode.set(mode);
			await Promise.resolve();
			expect(document.body.style.cssText).toBe(screenStyle);
			expect(control.parentElement!.style.cssText).toBe(portalStyle);
		}
		expect(document.body.style.colorScheme).toBe('light');
		expect(control.parentElement!.style.colorScheme).toBe('dark');
		appColorMode.set('dark');
		nested.update({ gameType: 'trivia' });
		expect(card.style.getPropertyValue('--party-primary')).toBe('#0ea5e9');
		expect(card.style.colorScheme).toBe('dark');
		expect(card.style.getPropertyValue('--party-bg-a')).toBe('#111827');
		appColorMode.set('light');
		expect(card.style.colorScheme).toBe('light');
		expect(card.style.getPropertyValue('--party-bg-a')).toBe('#f8fff1');
		screen.update({ gameType: 'trivia', screen: true });
		expect(document.body.hasAttribute('data-presentation')).toBe(false);
		expect(document.body.style.getPropertyValue('--party-primary')).toBe('');
	});
});
