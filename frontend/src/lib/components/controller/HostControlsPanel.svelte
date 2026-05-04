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

	function hostActionLabel(action?: NextHostAction): string {
		switch (action?.kind) {
			case 'answer_reveal':
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
	const nextActionPreview = $derived({
		label: primaryActionLabel,
		title:
			nextHostAction?.kind === 'blocked_review'
				? $messages.gameplay.nextStateReviewHelp
				: (nextHostAction?.title ?? '')
	});
	const primaryActionDisabled = $derived(Boolean(nextHostAction?.disabled));

	function runPrimaryHostAction() {
		if (nextHostAction?.kind === 'reactivate_buzzers') {
			onToggleBuzzer();
			return;
		}
		onNextStep();
	}
</script>

<section class="card stack-md">
	<h2 class="label-title text-2xl">{$messages.gameplay.hostControls}</h2>
	<div class="grid gap-2 sm:grid-cols-3">
		<p class="rounded-xl bg-white/70 px-3 py-2 text-sm font-semibold text-slate-700">
			<span class="block text-xs font-black uppercase text-slate-500"
				>{$messages.gameplay.phaseLabel}</span
			>
			{formatPhaseLabel(lobbyPhase)}
		</p>
		<p class="rounded-xl bg-white/70 px-3 py-2 text-sm font-semibold text-slate-700">
			<span class="block text-xs font-black uppercase text-slate-500"
				>{$messages.gameplay.submissionsLabel}</span
			>
			{submissionCount}
		</p>
		<p class="rounded-xl bg-white/70 px-3 py-2 text-sm font-semibold text-slate-700">
			<span class="block text-xs font-black uppercase text-slate-500"
				>{$messages.gameplay.pendingReviewLabel}</span
			>
			{pendingReviewCount}
		</p>
	</div>
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
	<div class="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3">
		<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
			<div>
				<p class="text-xs font-black uppercase tracking-[0.14em] text-sky-700">
					{$messages.gameplay.nextStatePreview}
				</p>
				<p class="mt-1 text-sm font-bold text-slate-950">{nextActionPreview.label}</p>
				{#if nextActionPreview.title}
					<p class="mt-1 wrap-break-word text-sm text-slate-700">{nextActionPreview.title}</p>
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
	{#if isBuzzerStep}
		<div
			class={`rounded-2xl border px-4 py-3 ${
				shouldPrioritizeBuzzer
					? 'border-amber-200 bg-amber-50'
					: buzzerActive
						? 'border-emerald-200 bg-emerald-50'
						: 'border-slate-200 bg-white/70'
			}`}
		>
			<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
				<div>
					<p class="text-sm font-black uppercase tracking-[0.14em] text-slate-500">
						{$messages.gameplay.buzzer}
					</p>
					<p class="mt-1 text-sm font-semibold text-slate-700">
						{buzzerActive
							? $messages.gameplay.buzzerOpenForPlayers
							: shouldPrioritizeBuzzer
								? $messages.gameplay.buzzerReadyToReactivate
								: $messages.gameplay.buzzerClosed}
					</p>
					{#if disabledBuzzerPlayerIds.length > 0}
						<p class="mt-1 text-xs font-semibold text-slate-500">
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
	<div class="grid gap-3 sm:grid-cols-2">
		<button
			type="button"
			class="btn btn-ghost w-full"
			onclick={onPreviousStep}
			disabled={displayPhase !== 'answer_reveal'}
		>
			{$messages.gameplay.previous}
		</button>
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
	</div>
	{#if hasControllableMedia}
		<div class="rounded-2xl border border-slate-200 bg-white/70 p-3">
			<p class="text-sm font-black uppercase tracking-[0.14em] text-slate-500">
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
			<label
				class="mt-3 grid gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-700"
			>
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
