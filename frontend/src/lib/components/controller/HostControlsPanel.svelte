<script lang="ts">
	import { formatPhaseLabel, messages } from '$lib/i18n';

	interface HostControlsPanelProps {
		activeStep?: RuntimeStepState;
		buzzerActive: boolean;
		displayPhase: string;
		hostEnabled: boolean;
		lobbyPhase: string;
		pendingReviewCount: number;
		scoreboardVisible: boolean;
		submissionCount: number;
		submittedPlayerNames: string[];
		onEvaluateStep: () => void;
		onNextStep: () => void;
		onPreviousStep: () => void;
		onResetStep: () => void;
		onToggleBuzzer: () => void;
		onToggleMediaPlayback: () => void;
		onToggleScoreboardVisibility: () => void;
	}

	let {
		activeStep,
		buzzerActive,
		displayPhase,
		hostEnabled,
		lobbyPhase,
		pendingReviewCount,
		scoreboardVisible,
		submissionCount,
		submittedPlayerNames,
		onEvaluateStep,
		onNextStep,
		onPreviousStep,
		onResetStep,
		onToggleBuzzer,
		onToggleMediaPlayback,
		onToggleScoreboardVisibility
	}: HostControlsPanelProps = $props();

	const nextStepLabel = $derived.by(() => {
		if (displayPhase === 'answer_reveal') {
			return $messages.gameplay.advanceStep;
		}
		if (lobbyPhase === 'question_active') {
			return $messages.gameplay.next;
		}
		return $messages.gameplay.showAnswer;
	});

	const canAutoEvaluate = $derived(!hostEnabled || activeStep?.evaluation_type !== 'host_judged');
</script>

<section class="card stack-md">
	<h2 class="label-title text-2xl">{$messages.gameplay.hostControls}</h2>
	<p class="text-sm text-slate-600">
		{$messages.gameplay.phaseLabel}: {formatPhaseLabel(lobbyPhase)} ·
		{$messages.gameplay.submissionsLabel}: {submissionCount} ·
		{$messages.gameplay.pendingReviewLabel}: {pendingReviewCount}
	</p>
	{#if submittedPlayerNames.length > 0}
		<div class="flex flex-wrap gap-2">
			{#each submittedPlayerNames as name}
				<span class="badge bg-emerald-100 text-emerald-800">
					{name}
					{$messages.gameplay.answered}
				</span>
			{/each}
		</div>
	{/if}
	<div class="flex flex-wrap gap-3">
		<button
			type="button"
			class="btn btn-ghost"
			onclick={onPreviousStep}
			disabled={displayPhase !== 'answer_reveal'}
		>
			{$messages.gameplay.previous}
		</button>
		<button
			type="button"
			class="btn btn-primary"
			onclick={onNextStep}
			disabled={lobbyPhase === 'host_review' && pendingReviewCount > 0}
		>
			{nextStepLabel}
		</button>
		<button type="button" class="btn btn-ghost" onclick={onResetStep}>
			{$messages.gameplay.resetQuestion}
		</button>
		<button type="button" class="btn btn-ghost" onclick={onToggleScoreboardVisibility}>
			{scoreboardVisible ? $messages.gameplay.hideScoreboard : $messages.gameplay.showScoreboard}
		</button>
		{#if activeStep?.media?.type_ === 'video'}
			<button type="button" class="btn btn-ghost" onclick={onToggleMediaPlayback}>
				{activeStep.media.paused ? $messages.gameplay.resumeMedia : $messages.gameplay.pauseMedia}
			</button>
		{/if}
		{#if canAutoEvaluate}
			<button type="button" class="btn btn-ghost" onclick={onEvaluateStep}>
				{$messages.gameplay.autoEvaluate}
			</button>
		{/if}
		{#if activeStep?.input_kind === 'buzzer'}
			<button type="button" class="btn btn-ghost" onclick={onToggleBuzzer}>
				{buzzerActive ? $messages.gameplay.disableBuzzer : $messages.gameplay.enableEligibleBuzzers}
			</button>
		{/if}
	</div>
</section>
