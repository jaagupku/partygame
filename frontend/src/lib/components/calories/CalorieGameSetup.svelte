<script lang="ts">
	import { presentationScope } from '$lib/presentation/scope';
	import { resolvePresentation } from '$lib/presentation/registry';
	import { primePresentationAudio } from '$lib/presentation/audio-driver';
	import PresentationDecoration from '$lib/presentation/PresentationDecoration.svelte';
	import { beginDisplayFullscreen } from '$lib/display-fullscreen';
	import { onMount, untrack } from 'svelte';
	import { goto } from '$app/navigation';
	import { messages, locale } from '$lib/i18n';
	import CalorieAttribution from './CalorieAttribution.svelte';
	const copy = $derived({ ...$messages.priceGame, ...$messages.calorieGame });
	const {
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
	type Mode = 'guess' | 'compare' | 'mixed';
	type Availability = {
		captured_at: string | null;
		combinations: { mode: Mode; questions: number }[];
	};
	let mode = $state<Mode>(untrack(() => initialSettings?.calorie_settings?.mode ?? 'mixed'));
	let questions = $state(untrack(() => initialSettings?.calorie_settings?.questions ?? 10));
	let seconds = $state(untrack(() => initialSettings?.calorie_settings?.answer_seconds ?? 30));
	let revealSeconds = $state(untrack(() => initialSettings?.calorie_settings?.reveal_seconds ?? 4));
	let hostEnabled = $state(untrack(() => initialSettings?.host_enabled ?? false));
	let availability = $state<Availability | null>(null);
	let loading = $state(true);
	let failed = $state(false);
	let creating = $state(false);
	let createError = $state<'unavailable' | 'createFailed' | null>(null);
	const playable = $derived(
		availability?.combinations.some((c) => c.mode === mode && c.questions === questions) ?? false
	);
	async function load() {
		loading = true;
		failed = false;
		try {
			const response = await fetch('/api/v1/game-types/calorie_guessing/availability');
			if (!response.ok) throw new Error('Availability failed');
			const loaded: Availability = await response.json();
			availability = loaded;
		} catch {
			failed = true;
		} finally {
			loading = false;
		}
	}
	onMount(() => {
		void load();
	});
	async function create() {
		if (!playable || creating) return;
		creating = true;
		createError = null;
		let cancelAudio: (() => void) | undefined;
		let cancelFullscreen: (() => void) | undefined;
		let openedDisplay = false;
		try {
			if (onsubmit) {
				await onsubmit({
					game_type: 'calorie_guessing',
					host_enabled: hostEnabled,
					calorie_settings: {
						mode,
						questions,
						answer_seconds: seconds,
						reveal_seconds: revealSeconds
					}
				});
				return;
			}
			if (resolvePresentation('calorie_guessing')?.audio) cancelAudio = primePresentationAudio();
			cancelFullscreen = beginDisplayFullscreen();
			const response = await fetch('/api/v1/lobby/create', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					game_type: 'calorie_guessing',
					host_enabled: hostEnabled,
					calorie_settings: {
						mode,
						questions,
						answer_seconds: seconds,
						reveal_seconds: revealSeconds
					}
				})
			});
			if (!response.ok) {
				createError = response.status === 409 ? 'unavailable' : 'createFailed';
				return;
			}
			const lobby: Lobby = await response.json();
			await goto(`/host/${lobby.join_code}`);
			openedDisplay = true;
		} catch {
			createError = 'createFailed';
		} finally {
			if (!openedDisplay) {
				cancelFullscreen?.();
				cancelAudio?.();
			}
			creating = false;
		}
	}
</script>

<div
	class="studio-setup"
	use:presentationScope={{ gameType: 'calorie_guessing', screen: !onsubmit }}
>
	{#if !onsubmit}<PresentationDecoration gameType="calorie_guessing" />{/if}

	<p class="studio-eyebrow">{$messages.calorieStudio.prepare}</p>
	<h1 class="page-title">{copy.title}</h1>
	<p class="page-subtitle">{copy.subtitle}</p>
	<p class="mb-4 theme-text-muted">{copy.selection}</p>
	<div class="stack-lg">
		<p>{copy.rules}</p>
		<p class="theme-text-muted">{copy.priceBasis}</p>
		{#if loading}<p role="status">{copy.loading}</p>
		{:else if failed}<div role="alert">
				<p>{copy.loadFailed}</p>
				<button class="btn btn-primary" onclick={load}>{copy.retry}</button>
			</div>
		{:else}
			<fieldset disabled={creating} class="card grid min-w-0 gap-4 sm:grid-cols-2">
				<label class="input-wrap"
					><span class="label-title">{copy.mode}</span><select class="input" bind:value={mode}
						>{#each ['guess', 'compare', 'mixed'] as option}<option value={option}
								>{copy[option as Mode]}</option
							>{/each}</select
					></label
				>

				<label class="input-wrap"
					><span class="label-title">{copy.questions}</span><select
						class="input"
						bind:value={questions}
						>{#each [5, 10, 15, 20] as value}<option {value}>{value}</option>{/each}</select
					></label
				>
				<label class="input-wrap"
					><span class="label-title">{copy.answerTime}</span><select
						class="input"
						bind:value={seconds}
						>{#each [15, 30, 45, 60] as value}<option {value}>{value} {copy.seconds}</option
							>{/each}</select
					></label
				>
				{#if !hostEnabled}
					<label class="input-wrap"
						><span class="label-title">{copy.revealTime}</span><select
							class="input"
							bind:value={revealSeconds}
							>{#each [4, 6, 8, 10, 15] as value}<option {value}>{value} {copy.seconds}</option
								>{/each}</select
						></label
					>
				{/if}
				<label class="input-wrap"
					><span class="label-title">{copy.progression}</span><select
						class="input"
						bind:value={hostEnabled}
						><option value={false}>{copy.automatic}</option><option value={true}
							>{copy.hostPaced}</option
						></select
					></label
				>
			</fieldset>
			{#if availability?.captured_at}<p class="theme-text-muted text-sm">
					{copy.captured}: {new Date(availability.captured_at).toLocaleDateString($locale)}
				</p>{/if}
			{#if !playable}<p role="status">{copy.unavailable}</p>
				<button class="btn btn-ghost" onclick={load}>{copy.retry}</button>{/if}
			{#if createError}<p role="alert">{copy[createError]}</p>{/if}
			<button class="btn btn-primary min-h-16" disabled={!playable || creating} onclick={create}
				>{creating
					? onsubmit
						? $messages.continueGame.preparing
						: $messages.gameCatalog.creating
					: (submitLabel ?? $messages.common.createGame)}</button
			>
		{/if}
		{#if oncancel}<button class="btn btn-ghost" disabled={creating} onclick={oncancel}
				>{$messages.common.back}</button
			>{:else}<a class="btn btn-ghost" href="/">{$messages.common.back}</a>{/if}
	</div>

	<CalorieAttribution download />
</div>
