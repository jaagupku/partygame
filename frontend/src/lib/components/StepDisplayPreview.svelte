<script lang="ts">
	import GameConnectionStatus from '$lib/components/GameConnectionStatus.svelte';
	import QuestionCard from '$lib/components/QuestionCard.svelte';
	import Timer from '$lib/components/util/Timer.svelte';

	interface StepDisplayPreviewProps {
		step?: RuntimeStepState;
		revealedSubmission?: RevealedSubmission;
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
</script>

<div class={`mt-0 ${stageLayout ? 'flex h-full min-h-0 flex-col gap-5' : 'stack-lg'}`}>
	<div class={stageLayout ? 'px-1' : ''}>
		{#if showTitle}
			<h1 class="page-title">{title}</h1>
		{/if}
		<p class={`page-subtitle ${stageLayout ? 'text-left' : ''}`}>
			Phase: <span class="font-bold">{phaseLabel}</span> · Submissions: {submissionCount} · Pending review:
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
		title="Now Playing"
		variant={stageLayout ? 'stage' : 'default'}
	/>

	{#if countdown > 0}
		<div class={`card w-full p-4 md:p-5 ${stageLayout ? '' : 'mx-auto max-w-3xl'}`}>
			<Timer {countdown} />
			<p class="mt-3 text-center text-sm text-slate-600">
				{step?.timer.enforced ? 'Timer is enforced' : 'Timer is advisory'}
			</p>
		</div>
	{/if}
</div>
