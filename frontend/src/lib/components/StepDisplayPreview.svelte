<script lang="ts">
	import QuestionCard from '$lib/components/QuestionCard.svelte';
	import Timer from '$lib/components/util/Timer.svelte';

	interface StepDisplayPreviewProps {
		step?: RuntimeStepState;
		revealedSubmission?: RevealedSubmission;
		title?: string;
		phaseLabel?: string;
		connectionLabel?: string;
		submissionCount?: number;
		pendingReviewCount?: number;
		countdown?: number;
	}

	let {
		step,
		revealedSubmission,
		title = 'Big Screen Preview',
		phaseLabel = 'question_active',
		connectionLabel = 'Preview',
		submissionCount = 0,
		pendingReviewCount = 0,
		countdown = 0
	}: StepDisplayPreviewProps = $props();
</script>

<div class="stack-lg">
	<div>
		<h1 class="page-title">{title}</h1>
		<p class="page-subtitle">
			Phase: <span class="font-bold">{phaseLabel}</span> · Submissions: {submissionCount} · Pending review:
			{pendingReviewCount}
		</p>
		<p class="page-subtitle mt-2">Connection: {connectionLabel}</p>
	</div>

	<QuestionCard {step} {revealedSubmission} title="Now Playing" />

	{#if countdown > 0}
		<div class="card mx-auto max-w-64">
			<Timer {countdown} />
			<p class="text-center text-sm text-slate-600">
				{step?.timer.enforced ? 'Timer is enforced' : 'Timer is advisory'}
			</p>
		</div>
	{/if}
</div>
