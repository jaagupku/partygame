<script lang="ts">
	import { messages } from '$lib/i18n';
	import type { PresentationSystem } from './system';
	let { system, phone = false }: { system: PresentationSystem; phone?: boolean } = $props();
	const settings = $derived(system.settings);
	const blocked = $derived(system.blocked);
</script>

<details class="presentation-audio card" class:phone data-presentation-audio>
	<summary>{$messages.presentationAudio.title}</summary>
	<div class="grid gap-3 pt-3">
		{#if $blocked}<button class="btn btn-primary" onclick={() => system.activate()}
				>{$messages.presentationAudio.enable}</button
			>{/if}
		{#if !phone}
			<label
				><input
					type="checkbox"
					checked={$settings.musicEnabled}
					onchange={(e) => {
						settings.update({ musicEnabled: e.currentTarget.checked });
						system.activate();
					}}
				/>
				{$messages.presentationAudio.music}</label
			>
			<label
				>{$messages.presentationAudio.musicVolume}<input
					type="range"
					min="0"
					max="100"
					value={$settings.musicVolume * 100}
					oninput={(e) => settings.update({ musicVolume: Number(e.currentTarget.value) / 100 })}
				/></label
			>
		{/if}
		<label
			><input
				type="checkbox"
				checked={$settings.effectsEnabled}
				onchange={(e) => {
					settings.update({ effectsEnabled: e.currentTarget.checked });
					system.activate();
				}}
			/>
			{phone ? $messages.presentationAudio.personal : $messages.presentationAudio.effects}</label
		>
		<label
			>{$messages.presentationAudio.effectsVolume}<input
				type="range"
				min="0"
				max="100"
				value={$settings.effectsVolume * 100}
				oninput={(e) => settings.update({ effectsVolume: Number(e.currentTarget.value) / 100 })}
			/></label
		>
	</div>
</details>

<style>
	.presentation-audio {
		position: fixed;
		top: 0.75rem;
		right: 0.75rem;
		z-index: 40;
		padding: 0.65rem;
		max-width: min(20rem, calc(100vw - 1.5rem));
		font-size: 0.875rem;
		background: var(--party-surface-strong);
		backdrop-filter: blur(16px);
	}
	.presentation-audio.phone {
		position: relative;
		top: auto;
		right: auto;
		width: fit-content;
		margin: 0 0 0.5rem auto;
	}
	summary {
		cursor: pointer;
		font-weight: 800;
	}
	label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
	}
	input[type='range'] {
		width: 100%;
		min-height: 1.75rem;
	}
</style>
