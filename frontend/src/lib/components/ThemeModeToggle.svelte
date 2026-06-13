<script lang="ts">
	import 'iconify-icon';
	import { appColorMode, type AppColorMode } from '$lib/theme';
	import { messages } from '$lib/i18n';

	const modes: { value: AppColorMode; icon: string }[] = [
		{ value: 'light', icon: 'fluent:weather-sunny-16-filled' },
		{ value: 'dark', icon: 'fluent:weather-moon-16-filled' },
		{ value: 'system', icon: 'fluent:desktop-16-filled' }
	];

	function modeLabel(mode: AppColorMode) {
		if (mode === 'light') {
			return $messages.theme.light;
		}
		if (mode === 'dark') {
			return $messages.theme.dark;
		}
		return $messages.theme.system;
	}
</script>

<div class="theme-mode-toggle" aria-label={$messages.theme.appTheme}>
	{#each modes as mode}
		<button
			type="button"
			class:theme-mode-active={$appColorMode === mode.value}
			aria-label={modeLabel(mode.value)}
			aria-pressed={$appColorMode === mode.value}
			title={modeLabel(mode.value)}
			onclick={() => appColorMode.set(mode.value)}
		>
			<iconify-icon icon={mode.icon}></iconify-icon>
		</button>
	{/each}
</div>

<style lang="postcss">
	.theme-mode-toggle {
		display: inline-flex;
		align-items: center;
		gap: 0.15rem;
		border: 1px solid var(--party-border);
		border-radius: 999px;
		background: var(--party-surface-strong);
		padding: 0.15rem;
		box-shadow: 0 10px 25px rgb(15 23 42 / 0.08);
	}

	.theme-mode-toggle button {
		display: grid;
		width: 2rem;
		height: 2rem;
		place-items: center;
		border-radius: 999px;
		color: var(--party-subtle);
		transition:
			background 150ms ease,
			color 150ms ease,
			box-shadow 150ms ease;
	}

	.theme-mode-toggle button.theme-mode-active {
		background: var(--party-primary);
		color: white;
		box-shadow: 0 3px 10px rgb(15 23 42 / 0.14);
	}
</style>
