<script lang="ts">
	import GameConnectionStatus from '$lib/components/GameConnectionStatus.svelte';
	import QuestionCard from '$lib/components/QuestionCard.svelte';
	import Timer from '$lib/components/util/Timer.svelte';
	import { messages } from '$lib/i18n';
	import { formatRevealValue, isOptionRevealStep, isOrderingRevealStep } from '$lib/reveal-format';

	interface StepDisplayPreviewProps {
		step?: RuntimeStepState;
		revealedSubmission?: RevealedSubmission;
		revealedAnswer?: RevealedAnswer;
		buzzerActive?: boolean;
		buzzedPlayerId?: string;
		buzzedPlayerName?: string;
		displayPhase?: string;
		phaseLabel?: string;
		connectionLabel?: string;
		layoutMode?: 'default' | 'host-stage';
		showDisconnectedChip?: boolean;
		countdown?: number;
		connected?: boolean | null;
		submissionCount?: number;
	}

	let {
		step,
		revealedSubmission,
		revealedAnswer,
		buzzerActive = false,
		buzzedPlayerName,
		displayPhase = 'question_active',
		phaseLabel = 'question_active',
		connectionLabel = '',
		layoutMode = 'default',
		showDisconnectedChip = false,
		countdown = 0,
		connected = null,
		submissionCount = 0
	}: StepDisplayPreviewProps = $props();

	let lastSubmissionCount = $state(0);
	let hasSeenSubmissionCount = $state(false);
	let submissionPulseKey = $state(0);

	const stageLayout = $derived(layoutMode === 'host-stage');
	const showingAnswerReveal = $derived(displayPhase === 'answer_reveal');
	const showStageRevealCard = $derived(
		stageLayout &&
			showingAnswerReveal &&
			revealedAnswer &&
			!isOptionRevealStep(step) &&
			!isOrderingRevealStep(step)
	);
	const showSubmissionIndicator = $derived(
		stageLayout && submissionCount > 0 && !showingAnswerReveal
	);
	const showBuzzerWinner = $derived(stageLayout && Boolean(buzzedPlayerName));

	$effect(() => {
		if (hasSeenSubmissionCount && submissionCount > lastSubmissionCount) {
			submissionPulseKey += 1;
		}
		lastSubmissionCount = submissionCount;
		hasSeenSubmissionCount = true;
	});
</script>

<div
	class={`mt-0 ${stageLayout ? 'relative grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-2 overflow-hidden' : 'stack-lg'}`}
>
	<div>
		<GameConnectionStatus {connected} {connectionLabel} showInline={false} {showDisconnectedChip} />
	</div>

	{#if showSubmissionIndicator}
		<div class={`floating-stage-chip-wrap ${showBuzzerWinner ? 'floating-stage-chip-left' : ''}`}>
			{#key submissionPulseKey}
				<div class="submission-indicator card px-4 py-2">
					<span class="submission-dot" aria-hidden="true"></span>
					<span>{submissionCount} submitted</span>
				</div>
			{/key}
		</div>
	{/if}

	{#if showBuzzerWinner}
		{#key buzzedPlayerName}
			<div class="floating-stage-chip-wrap floating-stage-chip-right">
				<div
					class="buzzer-winner-impact card rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3"
				>
					<p class="text-xs font-black uppercase tracking-[0.22em] text-amber-700">
						{$messages.gameplay.buzzedInFirst}
					</p>
					<p class="mt-1 max-w-72 truncate text-2xl font-extrabold leading-tight text-slate-950">
						{buzzedPlayerName}
					</p>
				</div>
			</div>
		{/key}
	{/if}

	{#key step?.id ?? 'empty-step'}
		<div class="question-stage-enter">
			<QuestionCard
				{step}
				{revealedSubmission}
				{revealedAnswer}
				{buzzerActive}
				{buzzedPlayerName}
				{displayPhase}
				variant={stageLayout ? 'stage' : 'default'}
			/>
		</div>
	{/key}

	{#if showStageRevealCard}
		<div class="reveal-answer-card card w-full border-emerald-200 bg-emerald-50 p-4 md:p-5">
			<p class="text-center text-sm font-black uppercase tracking-[0.22em] text-emerald-700">
				{$messages.common.correctAnswer}
			</p>
			<p
				class="mt-3 text-center text-[clamp(1.4rem,3vw,2.6rem)] font-extrabold leading-tight text-slate-950"
			>
				{formatRevealValue(revealedAnswer?.value)}
			</p>
		</div>
	{:else if !showingAnswerReveal && countdown > 0}
		<div class="stage-footer grid gap-2">
			<div class={`card w-full p-3 md:p-4 ${stageLayout ? '' : 'mx-auto max-w-3xl'}`}>
				<Timer
					{countdown}
					totalDuration={step?.timer.seconds ?? countdown}
					paused={phaseLabel !== 'question_active'}
				/>
				<p class="mt-3 text-center text-sm text-slate-600">
					{step?.timer.enforced ? $messages.timer.timerEnforced : $messages.timer.timerAdvisory}
				</p>
			</div>
		</div>
	{/if}
</div>

<style>
	.question-stage-enter {
		min-height: 0;
		animation: question-enter 360ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
	}

	.reveal-answer-card {
		animation: answer-card-pop 520ms cubic-bezier(0.2, 0.9, 0.2, 1.2) both;
	}

	.floating-stage-chip-wrap {
		position: absolute;
		top: 0.7rem;
		left: 50%;
		z-index: 6;
		pointer-events: none;
		transform: translateX(-50%);
	}

	.floating-stage-chip-left {
		left: 38%;
	}

	.floating-stage-chip-right {
		left: auto;
		right: 1rem;
		transform: none;
	}

	.submission-indicator {
		display: inline-flex;
		align-items: center;
		gap: 0.55rem;
		border-color: rgb(191 219 254);
		background: rgb(239 246 255 / 0.94);
		color: rgb(30 64 175);
		font-size: 0.82rem;
		font-weight: 900;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		animation: submission-pulse 420ms ease-out both;
	}

	.submission-dot {
		width: 0.55rem;
		height: 0.55rem;
		border-radius: 999px;
		background: rgb(37 99 235);
		box-shadow: 0 0 0 0 rgb(37 99 235 / 0.34);
		animation: submission-dot-ping 900ms ease-out both;
	}

	.buzzer-winner-impact {
		position: relative;
		min-width: min(18rem, 38vw);
		box-shadow: 0 18px 36px rgb(146 64 14 / 0.14);
		animation: buzzer-winner-impact 520ms cubic-bezier(0.2, 0.95, 0.25, 1.25) both;
	}

	.buzzer-winner-impact::after {
		content: '';
		position: absolute;
		inset: -0.3rem;
		border: 2px solid rgb(245 158 11 / 0.55);
		border-radius: 1.15rem;
		pointer-events: none;
		animation: buzzer-winner-ring 680ms ease-out both;
	}

	@keyframes question-enter {
		from {
			opacity: 0;
			transform: translateY(0.85rem) scale(0.985);
		}

		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	@keyframes answer-card-pop {
		0% {
			opacity: 0;
			transform: translateY(0.5rem) scale(0.96);
			box-shadow: 0 0 0 rgb(16 185 129 / 0);
		}

		55% {
			opacity: 1;
			transform: translateY(0) scale(1.018);
			box-shadow: 0 0 34px rgb(16 185 129 / 0.28);
		}

		100% {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	@keyframes submission-pulse {
		0% {
			transform: translateY(0.35rem) scale(0.96);
			opacity: 0;
		}

		65% {
			transform: translateY(0) scale(1.04);
			opacity: 1;
		}

		100% {
			transform: translateY(0) scale(1);
			opacity: 1;
		}
	}

	@keyframes submission-dot-ping {
		0% {
			box-shadow: 0 0 0 0 rgb(37 99 235 / 0.38);
		}

		100% {
			box-shadow: 0 0 0 0.55rem rgb(37 99 235 / 0);
		}
	}

	@keyframes buzzer-winner-impact {
		0% {
			opacity: 0;
			transform: translateY(-0.4rem) scale(0.86);
		}

		62% {
			opacity: 1;
			transform: translateY(0) scale(1.055);
		}

		100% {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	@keyframes buzzer-winner-ring {
		0% {
			opacity: 0.8;
			transform: scale(0.92);
		}

		100% {
			opacity: 0;
			transform: scale(1.12);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.question-stage-enter,
		.reveal-answer-card,
		.submission-indicator,
		.submission-dot,
		.buzzer-winner-impact,
		.buzzer-winner-impact::after {
			animation: none;
		}
	}
</style>
