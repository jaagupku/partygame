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
	gameType: 'calorie_guessing',
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
		const scope = presentationScope(node, { gameType: 'calorie_guessing' });
		cleanups.push(scope.destroy);
		expect(node.style.getPropertyValue('--party-primary')).toBe('purple');
		cleanups.push(registerPresentation(profile));
		expect(
			selectPresentation({
				gameType: 'calorie_guessing',
				runId: 'r2',
				gameState: 'running'
			} as ControllerState)
		).toMatchObject({ profile, runId: 'r2', variant: 'receipt' });
		expect(
			selectPresentation({ game_type: 'trivia', run_id: 'r3' } as HostGameState).profile
		).toBeUndefined();
	});
	it('keeps authored screen and variant styles fixed while neutral scopes follow the app preference', async () => {
		cleanups.push(registerPresentation(profile));
		appColorMode.set('light');
		const marker = document.createElement('div');
		const card = document.createElement('div');
		document.body.append(marker, card);
		const screen = presentationScope(marker, { gameType: 'calorie_guessing', screen: true });
		cleanups.push(screen.destroy);
		expect(document.body.style.getPropertyValue('--party-primary')).toBe('#123456');
		expect(document.body.style.getPropertyValue('--party-soft-primary-bg')).toContain('#123456');
		const nested = presentationScope(card, { gameType: 'calorie_guessing', variant: 'receipt' });
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
