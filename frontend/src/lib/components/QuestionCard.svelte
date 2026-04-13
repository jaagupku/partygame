<script lang="ts">
	import { onMount } from 'svelte';
	import { Sound } from 'svelte-sound';
	import buzzerWav from '$lib/assets/sounds/buzzer.wav';
	import ImageQuestionMedia from '$lib/components/ImageQuestionMedia.svelte';
	import AudioQuestionMedia from '$lib/components/AudioQuestionMedia.svelte';
	import VideoQuestionMedia from '$lib/components/VideoQuestionMedia.svelte';

	interface QuestionCardProps {
		step?: RuntimeStepState;
		title?: string;
		revealedSubmission?: RevealedSubmission;
		revealedAnswer?: RevealedAnswer;
		buzzerActive?: boolean;
		buzzedPlayerId?: string;
		buzzedPlayerName?: string;
		displayPhase?: string;
		variant?: 'default' | 'stage';
	}

	let {
		step,
		title = 'Question',
		revealedSubmission,
		revealedAnswer,
		buzzerActive = false,
		buzzedPlayerId,
		buzzedPlayerName,
		displayPhase = 'question_active',
		variant = 'default'
	}: QuestionCardProps = $props();

	const buzzerSound = new Sound(buzzerWav, { volume: 0.55 });
	const stageVariant = $derived(variant === 'stage');
	const showingAnswerReveal = $derived(displayPhase === 'answer_reveal');
	const isBuzzerStep = $derived(step?.input_kind === 'buzzer');
	const shouldPauseMedia = $derived(isBuzzerStep && !buzzerActive);
	const shouldResumePausedMedia = $derived(isBuzzerStep && buzzerActive);
	let hasMounted = $state(false);
	let lastBuzzedPlayerId = $state('');

	onMount(() => {
		hasMounted = true;
		lastBuzzedPlayerId = buzzedPlayerId ?? '';
	});

	$effect(() => {
		if (!hasMounted) {
			return;
		}

		const nextBuzzedPlayerId = buzzedPlayerId ?? '';
		if (isBuzzerStep && nextBuzzedPlayerId && nextBuzzedPlayerId !== lastBuzzedPlayerId) {
			buzzerSound.play();
		}
		lastBuzzedPlayerId = nextBuzzedPlayerId;
	});

	function formatRevealValue(value: unknown): string {
		if (Array.isArray(value)) {
			return value.map((entry) => String(entry)).join(' · ');
		}
		if (value && typeof value === 'object') {
			return JSON.stringify(value);
		}
		return String(value ?? '');
	}
</script>

<section
	class={`question-card card stack-md overflow-hidden ${stageVariant ? 'question-card-stage' : ''}`}
>
	<h2 class={`label-title ${stageVariant ? 'text-4xl md:text-5xl' : 'text-3xl'}`}>{title}</h2>
	{#if step}
		<h3
			class={stageVariant
				? 'text-[clamp(2rem,4vw,4rem)] font-extrabold leading-tight'
				: 'text-3xl font-extrabold'}
		>
			{step.title}
		</h3>
		{#if step.body}
			<p
				class={stageVariant
					? 'max-w-[60rem] text-[clamp(1rem,2.2vw,2rem)] leading-relaxed'
					: 'text-xl'}
			>
				{step.body}
			</p>
		{/if}
		{#if step.media?.type_ === 'image'}
			<ImageQuestionMedia {step} {stageVariant} />
		{:else if step.media?.type_ === 'audio'}
			<AudioQuestionMedia src={step.media.src} {shouldPauseMedia} {shouldResumePausedMedia} />
		{:else if step.media?.type_ === 'video'}
			<VideoQuestionMedia {step} {stageVariant} {shouldPauseMedia} {shouldResumePausedMedia} />
		{/if}
		{#if isBuzzerStep && buzzedPlayerName}
			<div
				class={`rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 ${
					stageVariant ? 'text-xl md:text-3xl' : 'text-lg'
				}`}
			>
				<p class="text-sm font-black uppercase tracking-[0.22em] text-amber-700">Buzzed In</p>
				<p class="mt-2 font-extrabold leading-tight text-slate-950">{buzzedPlayerName}</p>
			</div>
		{/if}
		{#if showingAnswerReveal && revealedAnswer}
			<div
				class={`rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 ${
					stageVariant ? 'text-xl md:text-3xl' : 'text-lg'
				}`}
			>
				<p class="text-sm font-black uppercase tracking-[0.22em] text-emerald-700">
					Correct answer
				</p>
				<p class="mt-2 font-extrabold leading-tight text-slate-950">
					{formatRevealValue(revealedAnswer.value)}
				</p>
			</div>
		{:else if !showingAnswerReveal && revealedSubmission}
			<div
				class={`rounded-2xl bg-sky-50 px-4 py-3 ${stageVariant ? 'text-xl md:text-2xl' : 'text-lg'}`}
			>
				<span class="font-bold">Revealed answer:</span>
				{String(revealedSubmission.value)}
			</div>
		{/if}
	{:else}
		<p class="text-lg text-slate-500">Waiting for next question...</p>
	{/if}
</section>

<style lang="postcss">
	.question-card-stage {
		display: grid;
		grid-template-rows: auto auto auto minmax(0, 1fr) auto;
		height: 100%;
		min-height: 0;
		padding: 1.5rem;
	}
</style>
