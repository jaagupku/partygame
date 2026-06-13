<script lang="ts">
	import { formatPhaseLabel, messages } from '$lib/i18n';

	interface HostControlsPanelProps {
		activeStep?: RuntimeStepState;
		buzzerActive: boolean;
		disabledBuzzerPlayerIds: string[];
		displayPhase: string;
		hostEnabled: boolean;
		lobbyPhase: string;
		nextHostAction?: NextHostAction;
		pendingReviewCount: number;
		pendingSubmissionPlayerNames: string[];
		reviewingHistory: boolean;
		canReviewPrevious: boolean;
		scoreboardVisible: boolean;
		submissionCount: number;
		submittedPlayerNames: string[];
		onEvaluateStep: () => void;
		onNextStep: () => void;
		onPreviousStep: () => void;
		onResetStep: () => void;
		onRestartMedia: () => void;
		onSetMediaVolume: (volume: number) => void;
		onToggleBuzzer: () => void;
		onToggleMediaPlayback: () => void;
		onToggleScoreboardVisibility: () => void;
	}

	let {
		activeStep,
		buzzerActive,
		disabledBuzzerPlayerIds,
		displayPhase,
		hostEnabled,
		lobbyPhase,
		nextHostAction,
		pendingReviewCount,
		pendingSubmissionPlayerNames,
		reviewingHistory,
		canReviewPrevious,
		scoreboardVisible,
		submissionCount,
		submittedPlayerNames,
		onEvaluateStep,
		onNextStep,
		onPreviousStep,
		onResetStep,
		onRestartMedia,
		onSetMediaVolume,
		onToggleBuzzer,
		onToggleMediaPlayback,
		onToggleScoreboardVisibility
	}: HostControlsPanelProps = $props();

	const canAutoEvaluate = $derived(!hostEnabled || activeStep?.evaluation_type !== 'host_judged');
	const isBuzzerStep = $derived(activeStep?.input_kind === 'buzzer');
	const shouldPrioritizeBuzzer = $derived(nextHostAction?.kind === 'reactivate_buzzers');
	const hasControllableMedia = $derived(
		activeStep?.media?.type_ === 'audio' || activeStep?.media?.type_ === 'video'
	);
	const mediaVolumePercent = $derived(Math.round((activeStep?.media?.volume ?? 1) * 100));
	let pendingSubmissionsOpen = $state(false);

	function hostActionLabel(action?: NextHostAction): string {
		switch (action?.kind) {
			case 'answer_reveal':
				if (
					activeStep?.input_kind === 'drawing' &&
					activeStep.evaluation_type === 'favorite_vote'
				) {
					return displayPhase === 'drawing_vote'
						? $messages.gameplay.nextStateDrawingResults
						: $messages.gameplay.nextStateDrawingVote;
				}
				return $messages.gameplay.nextStateAnswerReveal;
			case 'next_question':
				return $messages.gameplay.nextStateQuestion;
			case 'round_intro':
				return $messages.gameplay.nextStateRoundIntro;
			case 'finale':
				return $messages.gameplay.nextStateFinale;
			case 'blocked_review':
				return $messages.gameplay.nextStateReview;
			case 'reactivate_buzzers':
				return $messages.gameplay.nextStateReactivateBuzzers;
			default:
				return displayPhase === 'answer_reveal'
					? $messages.gameplay.advanceStep
					: $messages.gameplay.next;
		}
	}

	const primaryActionLabel = $derived(hostActionLabel(nextHostAction));
	const previousActionDisabled = $derived(
		!canReviewPrevious || (!reviewingHistory && displayPhase !== 'answer_reveal')
	);
	const nextActionPreview = $derived({
		label: primaryActionLabel,
		title:
			nextHostAction?.kind === 'blocked_review'
				? $messages.gameplay.nextStateReviewHelp
				: (nextHostAction?.title ?? '')
	});
	const primaryActionDisabled = $derived(Boolean(nextHostAction?.disabled));

	function runPrimaryHostAction() {
		if (reviewingHistory) {
			onNextStep();
			return;
		}
		if (nextHostAction?.kind === 'reactivate_buzzers') {
			onToggleBuzzer();
			return;
		}
		onNextStep();
	}
</script>

<section class="card controller-compact-card host-controls-card stack-md">
	<h2 class="label-title text-2xl">{$messages.gameplay.hostControls}</h2>
	<div class="host-stats-grid grid grid-cols-2 gap-2 lg:grid-cols-4">
		<p class="host-stat-cell">
			<span class="theme-text-muted block text-xs font-black uppercase"
				>{$messages.gameplay.phaseLabel}</span
			>
			{formatPhaseLabel(lobbyPhase)}
		</p>
		<p class="host-stat-cell">
			<span class="theme-text-muted block text-xs font-black uppercase"
				>{$messages.gameplay.submissionsLabel}</span
			>
			{submissionCount}
		</p>
		<p class="host-stat-cell">
			<span class="theme-text-muted block text-xs font-black uppercase"
				>{$messages.gameplay.pendingReviewLabel}</span
			>
			{pendingReviewCount}
		</p>
		<div class="relative">
			<button
				type="button"
				class="host-stat-cell w-full text-left transition hover:opacity-85 focus:outline-none focus:ring-2 focus:ring-sky-400"
				aria-expanded={pendingSubmissionsOpen}
				onclick={() => (pendingSubmissionsOpen = !pendingSubmissionsOpen)}
			>
				<span class="theme-text-muted block text-xs font-black uppercase"
					>{$messages.gameplay.pendingSubmissionsLabel}</span
				>
				{pendingSubmissionPlayerNames.length}
			</button>
			{#if pendingSubmissionsOpen}
				<div
					class="theme-surface absolute right-0 z-20 mt-2 w-64 rounded-xl border p-3 text-sm shadow-lg"
				>
					<p class="theme-text font-bold">{$messages.gameplay.pendingSubmissionsLabel}</p>
					{#if pendingSubmissionPlayerNames.length === 0}
						<p class="theme-text-muted mt-2">{$messages.gameplay.noPendingSubmissions}</p>
					{:else}
						<ul class="theme-text mt-2 space-y-1">
							{#each pendingSubmissionPlayerNames as name}
								<li class="theme-surface-muted wrap-break-word rounded-lg px-2 py-1 font-semibold">
									{name}
								</li>
							{/each}
						</ul>
					{/if}
				</div>
			{/if}
		</div>
	</div>
	{#if submittedPlayerNames.length > 0}
		<div class="flex flex-wrap gap-2">
			{#each submittedPlayerNames as name}
				<span class="host-positive-badge badge">
					{name}
					{$messages.gameplay.answered}
				</span>
			{/each}
		</div>
	{/if}
	<div class="host-action-panel theme-soft-primary rounded-2xl border px-4 py-3">
		<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
			<div>
				<p class="text-xs font-black uppercase tracking-[0.14em]">
					{reviewingHistory
						? $messages.gameplay.reviewingPreviousReveal
						: $messages.gameplay.nextStatePreview}
				</p>
				<p class="theme-text mt-1 text-sm font-bold">{nextActionPreview.label}</p>
				{#if nextActionPreview.title}
					<p class="theme-text-muted mt-1 wrap-break-word text-sm">{nextActionPreview.title}</p>
				{/if}
			</div>
			<button
				type="button"
				class="btn btn-primary w-full sm:w-auto"
				onclick={runPrimaryHostAction}
				disabled={primaryActionDisabled}
			>
				{primaryActionLabel}
			</button>
		</div>
	</div>
	{#if isBuzzerStep && !reviewingHistory}
		<div
			class={`host-action-panel rounded-2xl border px-4 py-3 ${
				shouldPrioritizeBuzzer
					? 'theme-soft-warm'
					: buzzerActive
						? 'theme-soft-success'
						: 'theme-surface-muted'
			}`}
		>
			<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
				<div>
					<p class="theme-text-muted text-sm font-black uppercase tracking-[0.14em]">
						{$messages.gameplay.buzzer}
					</p>
					<p class="theme-text mt-1 text-sm font-semibold">
						{buzzerActive
							? $messages.gameplay.buzzerOpenForPlayers
							: shouldPrioritizeBuzzer
								? $messages.gameplay.buzzerReadyToReactivate
								: $messages.gameplay.buzzerClosed}
					</p>
					{#if disabledBuzzerPlayerIds.length > 0}
						<p class="theme-text-muted mt-1 text-xs font-semibold">
							{$messages.gameplay.lockedOut}: {disabledBuzzerPlayerIds.length}
						</p>
					{/if}
				</div>
				<button
					type="button"
					class={`btn w-full sm:w-auto ${
						shouldPrioritizeBuzzer || buzzerActive ? 'btn-primary' : 'btn-ghost'
					}`}
					onclick={onToggleBuzzer}
				>
					{buzzerActive
						? $messages.gameplay.disableBuzzer
						: $messages.gameplay.enableEligibleBuzzers}
				</button>
			</div>
		</div>
	{/if}
	<div class="host-button-grid grid gap-3 sm:grid-cols-2">
		<button
			type="button"
			class="btn btn-ghost w-full"
			onclick={onPreviousStep}
			disabled={previousActionDisabled}
		>
			{$messages.gameplay.previous}
		</button>
		{#if !reviewingHistory}
			<button type="button" class="btn btn-ghost w-full" onclick={onResetStep}>
				{$messages.gameplay.resetQuestion}
			</button>
			<button type="button" class="btn btn-ghost w-full" onclick={onToggleScoreboardVisibility}>
				{scoreboardVisible ? $messages.gameplay.hideScoreboard : $messages.gameplay.showScoreboard}
			</button>
			{#if canAutoEvaluate}
				<button type="button" class="btn btn-ghost w-full" onclick={onEvaluateStep}>
					{$messages.gameplay.autoEvaluate}
				</button>
			{/if}
		{/if}
	</div>
	{#if hasControllableMedia && !reviewingHistory}
		<div class="host-action-panel theme-surface-muted rounded-2xl border p-3">
			<p class="theme-text-muted text-sm font-black uppercase tracking-[0.14em]">
				{$messages.gameplay.videoPlayback}
			</p>
			<div class="mt-3 grid gap-3 sm:grid-cols-2">
				<button type="button" class="btn btn-ghost w-full" onclick={onToggleMediaPlayback}>
					{activeStep?.media?.paused
						? $messages.gameplay.resumeMedia
						: $messages.gameplay.pauseMedia}
				</button>
				<button type="button" class="btn btn-ghost w-full" onclick={onRestartMedia}>
					{$messages.gameplay.restartMedia}
				</button>
			</div>
			<label class="theme-surface mt-3 grid gap-2 rounded-xl border px-3 py-2 text-sm font-bold">
				<span>{$messages.gameplay.mediaVolume}</span>
				<div class="flex items-center gap-3">
					<input
						class="min-w-0 flex-1 accent-sky-500"
						type="range"
						min="0"
						max="100"
						step="5"
						value={mediaVolumePercent}
						oninput={(event) =>
							onSetMediaVolume(Number((event.currentTarget as HTMLInputElement).value) / 100)}
					/>
					<span class="w-12 text-right tabular-nums">{mediaVolumePercent}%</span>
				</div>
			</label>
		</div>
	{/if}
</section>

<style>
	@media (max-width: 640px) {
		.host-controls-card {
			gap: 0.6rem;
		}

		.host-stats-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
			gap: 0.45rem;
		}

		.host-stats-grid :global(.text-xs) {
			font-size: 0.62rem;
			line-height: 1;
			letter-spacing: 0.08em;
		}

		.host-action-panel {
			border-radius: 0.85rem;
			padding: 0.65rem;
		}

		.host-action-panel :global(.btn),
		.host-button-grid :global(.btn) {
			border-radius: 0.85rem;
			padding: 0.65rem 0.8rem;
			font-size: 1rem;
			line-height: 1.1;
		}

		.host-button-grid {
			gap: 0.45rem;
		}
	}

	.host-stat-cell {
		border-radius: 0.75rem;
		border: 1px solid color-mix(in srgb, var(--party-border), transparent 25%);
		background: var(--party-soft-surface);
		padding: 0.45rem 0.55rem;
		color: var(--party-ink);
		font-size: 0.82rem;
		font-weight: 700;
		line-height: 1.15;
	}

	.host-positive-badge {
		border: 1px solid var(--party-soft-success-border);
		background: var(--party-soft-success-bg);
		color: var(--party-soft-success-text);
	}

	@media (min-width: 641px) {
		.host-stat-cell {
			border-radius: 0.75rem;
			padding: 0.5rem 0.75rem;
			font-size: 0.875rem;
		}
	}
</style>
