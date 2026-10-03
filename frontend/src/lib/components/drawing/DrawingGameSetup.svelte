<script lang="ts">
	import { presentationScope } from '$lib/presentation/scope';
	import { resolvePresentation } from '$lib/presentation/registry';
	import { primePresentationAudio } from '$lib/presentation/audio-driver';
	import PresentationDecoration from '$lib/presentation/PresentationDecoration.svelte';
	import { beginDisplayFullscreen } from '$lib/display-fullscreen';
	import { onMount, untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { messages, locale, locales } from '$lib/i18n';
	let {
		initialSettings,
		onsubmit,
		oncancel,
		submitLabel
	}: {
		initialSettings?: GameSetupSettings;
		onsubmit?: (settings: GameSetupSettings) => Promise<void>;
		oncancel?: () => void;
		submitLabel?: string;
	} = $props();
	let options = $state<DrawingSettings>(
		untrack(
			() =>
				initialSettings?.drawing_settings ?? {
					writing_seconds: 90,
					drawing_seconds: 90,
					voting_seconds: 30,
					language: $locale
				}
		)
	);
	let hydrated = $state(false);
	onMount(() => {
		hydrated = true;
	});
	let busy = $state(false);
	let failed = $state(false);
	async function create(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		failed = false;
		const settings: GameSetupSettings = {
			game_type: 'drawing_mashup',
			host_enabled: false,
			drawing_settings: options
		};
		let cancelAudio: (() => void) | undefined;
		let cancelFullscreen: (() => void) | undefined;
		let openedDisplay = false;
		try {
			if (onsubmit) {
				await onsubmit(settings);
				return;
			}
			if (resolvePresentation('drawing_mashup')?.audio) cancelAudio = primePresentationAudio();
			cancelFullscreen = beginDisplayFullscreen();
			const response = await fetch('/api/v1/lobby/create', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(settings)
			});
			if (!response.ok) throw new Error('Create failed');
			const lobby: Lobby = await response.json();
			await goto(`/host/${lobby.join_code}`);
			openedDisplay = true;
		} catch {
			failed = true;
		} finally {
			if (!openedDisplay) {
				cancelFullscreen?.();
				cancelAudio?.();
			}
			busy = false;
		}
	}
</script>

<div
	style="display: contents"
	use:presentationScope={{ gameType: 'drawing_mashup', screen: !onsubmit }}
>
	<PresentationDecoration gameType="drawing_mashup" />

	<h1 class="page-title">{$messages.drawingMashup.title}</h1>
	<p class="page-subtitle">{$messages.drawingMashup.rules}</p>
	<form class="card stack-md mx-auto max-w-2xl" onsubmit={create}>
		<p>{$messages.drawingMashup.minimum}</p>
		<label class="stack-sm"
			>{$messages.drawingMashup.writingSeconds}<input
				class="input"
				type="number"
				min="30"
				max="300"
				required
				bind:value={options.writing_seconds}
			/></label
		>
		<label class="stack-sm"
			>{$messages.drawingMashup.drawingSeconds}<input
				class="input"
				type="number"
				min="30"
				max="300"
				required
				bind:value={options.drawing_seconds}
			/></label
		>
		<label class="stack-sm"
			>{$messages.drawingMashup.votingSeconds}<input
				class="input"
				type="number"
				min="10"
				max="120"
				required
				bind:value={options.voting_seconds}
			/></label
		>
		<label class="stack-sm"
			>{$messages.drawingMashup.language}<select class="input" bind:value={options.language}
				>{#each locales as language}<option value={language.code}>{language.label}</option
					>{/each}</select
			></label
		>
		{#if failed}<p role="alert">{$messages.drawingMashup.createFailed}</p>{/if}
		<button class="btn btn-primary" type="submit" disabled={busy || !hydrated}
			>{busy
				? $messages.gameCatalog.creating
				: (submitLabel ?? $messages.common.createGame)}</button
		>
		{#if oncancel}<button class="btn btn-ghost" type="button" onclick={oncancel} disabled={busy}
				>{$messages.common.cancel}</button
			>{/if}
	</form>
</div>
