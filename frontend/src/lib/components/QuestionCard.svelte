<script lang="ts">
	import { flip } from 'svelte/animate';
	import ImageQuestionMedia from '$lib/components/ImageQuestionMedia.svelte';
	import AudioQuestionMedia from '$lib/components/AudioQuestionMedia.svelte';
	import StepBodyMarkdown from '$lib/components/markdown/StepBodyMarkdown.svelte';
	import VideoQuestionMedia from '$lib/components/VideoQuestionMedia.svelte';
	import { messages } from '$lib/i18n';
	import {
		buildOrderingRevealItems,
		buildRevealedOptionStates,
		formatRevealValue,
		isOrderingRevealStep,
		isOptionRevealStep
	} from '$lib/reveal-format';

	interface QuestionCardProps {
		step?: RuntimeStepState;
		revealedSubmission?: RevealedSubmission;
		revealedAnswer?: RevealedAnswer;
		buzzerActive?: boolean;
		buzzedPlayerName?: string;
		displayPhase?: string;
		variant?: 'default' | 'stage';
	}

	let {
		step,
		revealedSubmission,
		revealedAnswer,
		buzzerActive = false,
		buzzedPlayerName,
		displayPhase = 'question_active',
		variant = 'default'
	}: QuestionCardProps = $props();

	const stageVariant = $derived(variant === 'stage');
	const showingAnswerReveal = $derived(displayPhase === 'answer_reveal');
	const optionRevealStep = $derived(isOptionRevealStep(step));
	const optionStates = $derived.by(() =>
		step && optionRevealStep ? buildRevealedOptionStates(step, revealedAnswer) : []
	);
	const showOptionGrid = $derived(Boolean(step?.input_options.length) && optionRevealStep);
	const orderingRevealStep = $derived(isOrderingRevealStep(step));
	const orderingItems = $derived.by(() =>
		step && orderingRevealStep
			? buildOrderingRevealItems(step, revealedAnswer, showingAnswerReveal)
			: []
	);
	const showOrderingList = $derived(Boolean(step?.input_options.length) && orderingRevealStep);
	const showInlineRevealedAnswer = $derived(
		showingAnswerReveal &&
			revealedAnswer &&
			!stageVariant &&
			!optionRevealStep &&
			!orderingRevealStep
	);
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
	const fullCreditPointsLabel = $derived(
		step ? `${step.max_points ?? step.evaluation_points} ${$messages.common.pointsWord}` : ''
	);

	function orderingItemKey(items: string[], item: string, index: number) {
		const occurrence = items.slice(0, index + 1).filter((value) => value === item).length;
		return `${item}::${occurrence}`;
	}
</script>

<section
	class={`question-card overflow-hidden ${
		stageVariant ? 'question-card-stage-shell question-card-stage' : 'card stack-md'
	} ${showingAnswerReveal ? 'question-card-reveal-pulse' : ''}`}
>
	{#if step}
		<div class="question-card-title-row">
			<h3
				class={`question-card-step-title ${
					stageVariant
						? 'text-[clamp(1.8rem,3.4vw,3.6rem)] font-extrabold leading-tight'
						: 'text-3xl font-extrabold'
				}`}
			>
				{step.title}
			</h3>
			<span class={`question-card-points-badge ${stageVariant ? 'points-badge-stage' : ''}`}>
				{fullCreditPointsLabel}
			</span>
		</div>
		{#if step.body}
			<StepBodyMarkdown source={step.body} {stageVariant} />
		{/if}
		<div class={`question-card-media ${stageVariant ? 'question-card-media-stage' : ''}`}>
			{#if step.media?.type_ === 'image'}
				<ImageQuestionMedia {step} {stageVariant} />
			{:else if step.media?.type_ === 'audio'}
				<AudioQuestionMedia
					src={step.media.src}
					loop={step.media.loop}
					volume={step.media.volume ?? 1}
					{shouldPauseMedia}
					{shouldResumePausedMedia}
					playbackRevision={step.media.playback_revision ?? 0}
				/>
			{:else if step.media?.type_ === 'video'}
				<VideoQuestionMedia
					{step}
					{stageVariant}
					volume={step.media.volume ?? 1}
					{shouldPauseMedia}
					{shouldResumePausedMedia}
				/>
			{/if}
		</div>
		{#if showOptionGrid}
			<div
				class={`question-card-options grid gap-2 ${
					stageVariant
						? 'grid-cols-1 text-base sm:grid-cols-2 md:text-lg'
						: 'grid-cols-1 text-lg sm:grid-cols-2'
				}`}
			>
				{#each optionStates as optionState, optionIndex (optionIndex)}
					<div
						class={`option-flip ${showingAnswerReveal ? 'option-flip-revealed' : ''}`}
						style={`--option-delay: ${optionIndex * 90}ms`}
					>
						<div class="option-flip-inner">
							<div
								class={`option-face option-face-front ${
									stageVariant ? 'min-h-14 px-4 py-3' : 'min-h-16 px-4 py-4'
								}`}
							>
								<span class="option-text">{optionState.option}</span>
							</div>
							<div
								class={`option-face option-face-back ${
									optionState.correct ? 'option-face-correct' : 'option-face-wrong'
								} ${stageVariant ? 'min-h-14 px-4 py-3' : 'min-h-16 px-4 py-4'}`}
							>
								<span class="option-text">{optionState.option}</span>
								<span
									class={`option-points ${
										optionState.correct ? 'option-points-correct' : 'option-points-wrong'
									}`}
								>
									{optionState.pointsLabel}
								</span>
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
		{#if showOrderingList}
			<div
				class={`question-card-ordering grid gap-2 ${
					stageVariant ? 'text-base md:text-lg' : 'text-lg'
				} ${showingAnswerReveal ? 'question-card-ordering-revealed' : ''}`}
			>
				{#each orderingItems as item, itemIndex (orderingItemKey(orderingItems, item, itemIndex))}
					<div
						class={`ordering-display-row ${
							showingAnswerReveal ? 'ordering-display-row-revealed' : ''
						}`}
						animate:flip={{ duration: 420 }}
						style={`--ordering-delay: ${itemIndex * 85}ms`}
					>
						<span class="ordering-rank">#{itemIndex + 1}</span>
						<span class="ordering-text">{item}</span>
					</div>
				{/each}
			</div>
		{/if}
		{#if showInlineRevealedAnswer}
			<div
				class={`reveal-inline-pop question-card-status rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 ${
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
		grid-template-rows: auto auto auto minmax(0, 1fr) auto auto;
		gap: clamp(0.35rem, 0.8vh, 0.75rem);
		height: 100%;
		min-height: 0;
		min-width: 0;
		padding: clamp(0.5rem, 1.1vw, 1.25rem);
	}

	.question-card-stage-shell {
		position: relative;
		border-radius: 1.5rem;
		border: 0;
		background: rgb(255 255 255 / 0.38);
		box-shadow: none;
	}

	.question-card-reveal-pulse {
		animation: stage-reveal-pulse 620ms ease-out both;
	}

	.question-card-media-stage {
		display: grid;
		place-items: center;
		grid-row: 4;
		min-height: 0;
		min-width: 0;
		height: 100%;
		overflow: hidden;
	}

	.question-card-title-row {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: clamp(0.75rem, 2vw, 1.5rem);
		min-width: 0;
	}

	.question-card-step-title {
		min-width: 0;
		overflow-wrap: anywhere;
	}

	.question-card-points-badge {
		flex: 0 0 auto;
		margin-top: 0.15rem;
		border-radius: 999px;
		border: 1px solid rgb(191 219 254);
		background: rgb(239 246 255 / 0.92);
		color: rgb(30 64 175);
		font-size: 0.82rem;
		font-weight: 950;
		line-height: 1;
		padding: 0.55rem 0.75rem;
		white-space: nowrap;
	}

	.points-badge-stage {
		margin-top: 0.35rem;
		font-size: clamp(0.9rem, 1.2vw, 1.15rem);
		padding: 0.65rem 0.9rem;
	}

	.question-card-options {
		min-height: 0;
	}

	.question-card-ordering {
		min-height: 0;
		align-content: center;
	}

	.ordering-display-row {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		align-items: center;
		gap: 0.8rem;
		min-width: 0;
		border-radius: 1rem;
		border: 1px solid rgb(203 213 225);
		background: rgb(255 255 255 / 0.78);
		box-shadow: 0 1px 2px rgb(15 23 42 / 0.08);
		padding: 0.72rem 0.9rem;
	}

	.ordering-display-row-revealed {
		border-color: rgb(37 99 235 / 0.48);
		background: rgb(239 246 255 / 0.94);
		animation: ordering-reveal-land 520ms ease-out both;
		animation-delay: var(--ordering-delay);
	}

	.ordering-rank {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 3rem;
		border-radius: 999px;
		background: rgb(226 232 240 / 0.82);
		color: rgb(51 65 85);
		font-size: 0.8em;
		font-weight: 950;
		line-height: 1;
		padding: 0.45rem 0.65rem;
	}

	.ordering-display-row-revealed .ordering-rank {
		background: rgb(37 99 235);
		color: white;
	}

	.ordering-text {
		min-width: 0;
		overflow-wrap: anywhere;
		font-weight: 900;
		line-height: 1.15;
		color: rgb(15 23 42);
	}

	.question-card-status {
		min-height: 0;
	}

	.option-flip {
		perspective: 56rem;
		min-width: 0;
	}

	.option-flip-inner {
		position: relative;
		display: grid;
		transform-style: preserve-3d;
		transition: transform 520ms cubic-bezier(0.2, 0.8, 0.2, 1);
		transition-delay: var(--option-delay);
	}

	.option-flip-revealed .option-flip-inner {
		transform: rotateX(180deg);
	}

	.option-flip-revealed .option-face-correct {
		animation: correct-answer-lift 560ms cubic-bezier(0.2, 0.9, 0.2, 1.2) both;
		animation-delay: calc(var(--option-delay) + 620ms);
	}

	.option-face {
		grid-area: 1 / 1;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		min-width: 0;
		border-radius: 1rem;
		border: 1px solid rgb(203 213 225);
		background: rgb(255 255 255 / 0.78);
		box-shadow: 0 1px 2px rgb(15 23 42 / 0.08);
		backface-visibility: hidden;
	}

	.option-face-back {
		transform: rotateX(180deg);
	}

	.option-face-correct {
		border-color: rgb(4 120 87);
		background: rgb(5 150 105);
		color: white;
		box-shadow: 0 10px 24px rgb(6 78 59 / 0.22);
	}

	.option-face-wrong {
		border-color: rgb(190 18 60);
		background: rgb(225 29 72);
		color: white;
		box-shadow: 0 10px 24px rgb(136 19 55 / 0.22);
	}

	.option-text {
		min-width: 0;
		overflow-wrap: anywhere;
		font-weight: 900;
		line-height: 1.15;
	}

	.option-points {
		flex: 0 0 auto;
		border-radius: 999px;
		opacity: 0;
		padding: 0.35rem 0.65rem;
		font-size: 0.78em;
		font-weight: 950;
		line-height: 1;
	}

	.option-flip-revealed .option-points {
		animation: points-badge-pop 340ms cubic-bezier(0.2, 0.9, 0.2, 1.25) both;
		animation-delay: calc(var(--option-delay) + 500ms);
	}

	.option-points-correct {
		background: rgb(6 95 70);
		color: white;
	}

	.option-points-wrong {
		background: rgb(159 18 57);
		color: white;
	}

	.reveal-inline-pop {
		animation: answer-card-pop 480ms cubic-bezier(0.2, 0.9, 0.2, 1.2) both;
	}

	@keyframes stage-reveal-pulse {
		0% {
			box-shadow: 0 0 0 rgb(14 165 233 / 0);
			transform: scale(1);
		}

		42% {
			box-shadow: 0 0 38px rgb(14 165 233 / 0.22);
			transform: scale(1.006);
		}

		100% {
			box-shadow: 0 0 0 rgb(14 165 233 / 0);
			transform: scale(1);
		}
	}

	@keyframes points-badge-pop {
		0% {
			opacity: 0;
			transform: translateX(0.35rem) scale(0.72);
		}

		68% {
			opacity: 1;
			transform: translateX(0) scale(1.12);
		}

		100% {
			opacity: 1;
			transform: translateX(0) scale(1);
		}
	}

	@keyframes ordering-reveal-land {
		0% {
			filter: brightness(1);
			box-shadow: 0 1px 2px rgb(15 23 42 / 0.08);
		}

		48% {
			filter: brightness(1.06);
			box-shadow: 0 0 24px rgb(37 99 235 / 0.2);
		}

		100% {
			filter: brightness(1);
			box-shadow: 0 1px 2px rgb(15 23 42 / 0.08);
		}
	}

	@keyframes correct-answer-lift {
		0%,
		100% {
			filter: brightness(1);
			transform: rotateX(180deg) translateY(0);
		}

		48% {
			filter: brightness(1.1);
			transform: rotateX(180deg) translateY(-0.18rem);
		}
	}

	@keyframes answer-card-pop {
		0% {
			opacity: 0;
			transform: translateY(0.4rem) scale(0.96);
			box-shadow: 0 0 0 rgb(16 185 129 / 0);
		}

		62% {
			opacity: 1;
			transform: translateY(0) scale(1.018);
			box-shadow: 0 0 30px rgb(16 185 129 / 0.25);
		}

		100% {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.question-card-reveal-pulse,
		.option-flip-revealed .option-face-correct,
		.option-flip-revealed .option-points,
		.ordering-display-row-revealed,
		.reveal-inline-pop {
			animation: none;
		}

		.option-points {
			opacity: 1;
		}

		.option-flip-inner {
			transform-style: flat;
			transition: none;
		}

		.option-flip-revealed .option-flip-inner {
			transform: none;
		}

		.option-face {
			backface-visibility: visible;
		}

		.option-face-front {
			opacity: 1;
		}

		.option-flip-revealed .option-face-front {
			opacity: 0;
		}

		.option-face-back {
			opacity: 0;
			transform: none;
		}

		.option-flip-revealed .option-face-back {
			opacity: 1;
		}
	}
</style>
