<script lang="ts">
	import GameConnectionStatus from '$lib/components/GameConnectionStatus.svelte';
	import QuestionCard from '$lib/components/QuestionCard.svelte';
	import Timer from '$lib/components/util/Timer.svelte';

	interface StepDisplayPreviewProps {
		step?: RuntimeStepState;
		revealedSubmission?: RevealedSubmission;
		revealedAnswer?: RevealedAnswer;
		buzzerActive?: boolean;
		displayPhase?: string;
		title?: string;
		phaseLabel?: string;
		connectionLabel?: string;
		layoutMode?: 'default' | 'host-stage';
		showConnectionInline?: boolean;
		showDisconnectedChip?: boolean;
		submissionCount?: number;
		pendingReviewCount?: number;
		countdown?: number;
	}

	let {
		step,
		revealedSubmission,
		revealedAnswer,
		buzzerActive = false,
		displayPhase = 'question_active',
		title = '',
		phaseLabel = 'question_active',
		connectionLabel = 'Preview',
		layoutMode = 'default',
		showConnectionInline = true,
		showDisconnectedChip = false,
		submissionCount = 0,
		pendingReviewCount = 0,
		countdown = 0
	}: StepDisplayPreviewProps = $props();

	const showTitle = $derived(Boolean(title?.trim()));
	const stageLayout = $derived(layoutMode === 'host-stage');
	const showingAnswerReveal = $derived(displayPhase === 'answer_reveal');
</script>

<div
	class={`mt-0 ${stageLayout ? 'grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-4 overflow-hidden' : 'stack-lg'}`}
>
	<div class={stageLayout ? 'px-1 pb-1' : ''}>
		{#if showTitle}
			<h1 class={`page-title ${stageLayout ? 'text-left text-3xl md:text-4xl' : ''}`}>{title}</h1>
		{/if}
		<p class={`page-subtitle ${stageLayout ? 'text-left text-base md:text-lg' : ''}`}>
			Phase:
			<span class="font-bold">{showingAnswerReveal ? 'answer_reveal' : phaseLabel}</span>
			· Submissions: {submissionCount} · Pending review:
			{pendingReviewCount}
		</p>
		<GameConnectionStatus
			{connectionLabel}
			showInline={showConnectionInline}
			{showDisconnectedChip}
		/>
	</div>

	<QuestionCard
		{step}
		{revealedSubmission}
		{revealedAnswer}
		{buzzerActive}
		{displayPhase}
		title={showingAnswerReveal ? 'Answer Reveal' : 'Now Playing'}
		variant={stageLayout ? 'stage' : 'default'}
	/>

	{#if countdown > 0 && !showingAnswerReveal}
		<div class={`card w-full p-4 md:p-5 ${stageLayout ? '' : 'mx-auto max-w-3xl'}`}>
			<Timer
				{countdown}
				totalDuration={step?.timer.seconds ?? countdown}
				paused={phaseLabel !== 'question_active'}
			/>
			<p class="mt-3 text-center text-sm text-slate-600">
				{step?.timer.enforced ? 'Timer is enforced' : 'Timer is advisory'}
			</p>
		</div>
	{/if}
</div>
