<script lang="ts">
	import ImageQuestionMedia from '$lib/components/ImageQuestionMedia.svelte';
	import AudioQuestionMedia from '$lib/components/AudioQuestionMedia.svelte';
	import VideoQuestionMedia from '$lib/components/VideoQuestionMedia.svelte';
	import { messages } from '$lib/i18n';
	import { formatRevealValue } from '$lib/reveal-format';

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
		title = '',
		revealedSubmission,
		revealedAnswer,
		buzzerActive = false,
		buzzedPlayerId,
		buzzedPlayerName,
		displayPhase = 'question_active',
		variant = 'default'
	}: QuestionCardProps = $props();

	const stageVariant = $derived(variant === 'stage');
	const showCardTitle = $derived(Boolean(title?.trim()));
	const showingAnswerReveal = $derived(displayPhase === 'answer_reveal');
	const showInlineRevealedAnswer = $derived(showingAnswerReveal && revealedAnswer && !stageVariant);
	const isBuzzerStep = $derived(step?.input_kind === 'buzzer');
	const shouldPauseMedia = $derived(
		Boolean(step?.media?.paused) || (isBuzzerStep && !buzzerActive)
	);
	const shouldResumePausedMedia = $derived.by(() => {
		const media = step?.media;
		if (!media) {
			return false;
		}
		return !media.paused && (!isBuzzerStep || buzzerActive);
	});
</script>

<section
	class={`question-card overflow-hidden ${stageVariant ? 'question-card-stage-shell question-card-stage' : 'card stack-md'}`}
>
	{#if showCardTitle}
		<h2
			class={`label-title question-card-kicker ${stageVariant ? 'text-4xl md:text-5xl' : 'text-3xl'}`}
		>
			{title}
		</h2>
	{/if}
	{#if step}
		<h3
			class={`question-card-step-title ${
				stageVariant
					? 'text-[clamp(1.8rem,3.4vw,3.6rem)] font-extrabold leading-tight'
					: 'text-3xl font-extrabold'
			}`}
		>
			{step.title}
		</h3>
		{#if step.body}
			<p
				class={`question-card-body ${
					stageVariant ? 'max-w-[86rem] text-[clamp(1rem,1.8vw,1.7rem)] leading-snug' : 'text-xl'
				}`}
			>
				{step.body}
			</p>
		{/if}
		<div class={`question-card-media ${stageVariant ? 'question-card-media-stage' : ''}`}>
			{#if step.media?.type_ === 'image'}
				<ImageQuestionMedia {step} {stageVariant} />
			{:else if step.media?.type_ === 'audio'}
				<AudioQuestionMedia src={step.media.src} {shouldPauseMedia} {shouldResumePausedMedia} />
			{:else if step.media?.type_ === 'video'}
				<VideoQuestionMedia {step} {stageVariant} {shouldPauseMedia} {shouldResumePausedMedia} />
			{/if}
		</div>
		{#if isBuzzerStep && buzzedPlayerName}
			<div
				class={`question-card-status rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 ${
					stageVariant ? 'text-xl md:text-3xl' : 'text-lg'
				}`}
			>
				<p class="text-sm font-black uppercase tracking-[0.22em] text-amber-700">
					{$messages.gameplay.buzzedInFirst}
				</p>
				<p class="mt-2 font-extrabold leading-tight text-slate-950">{buzzedPlayerName}</p>
			</div>
		{/if}
		{#if showInlineRevealedAnswer}
			<div
				class={`question-card-status rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 ${
					stageVariant ? 'text-xl md:text-3xl' : 'text-lg'
				}`}
			>
				<p class="text-sm font-black uppercase tracking-[0.22em] text-emerald-700">
					{$messages.common.correctAnswer}
				</p>
				<p class="mt-2 font-extrabold leading-tight text-slate-950">
					{formatRevealValue(revealedAnswer?.value)}
				</p>
			</div>
		{:else if !showingAnswerReveal && revealedSubmission}
			<div
				class={`question-card-status rounded-2xl bg-sky-50 px-4 py-3 ${
					stageVariant ? 'text-xl md:text-2xl' : 'text-lg'
				}`}
			>
				<span class="font-bold">{$messages.common.revealedAnswer}:</span>
				{String(revealedSubmission.value)}
			</div>
		{/if}
	{:else}
		<p class="text-lg text-slate-500">{$messages.common.waitingForNextQuestion}</p>
	{/if}
</section>

<style lang="postcss">
	.question-card-stage {
		display: grid;
		grid-template-rows: auto auto auto minmax(0, 1fr) auto;
		gap: clamp(0.35rem, 0.8vh, 0.75rem);
		height: 100%;
		min-height: 0;
		padding: clamp(0.5rem, 1.1vw, 1.25rem);
	}

	.question-card-stage-shell {
		border-radius: 1.5rem;
		border: 0;
		background: rgb(255 255 255 / 0.38);
		box-shadow: none;
	}

	.question-card-media-stage {
		grid-row: 4;
		min-height: 0;
		height: 100%;
	}

	.question-card-status {
		min-height: 0;
	}
</style>
