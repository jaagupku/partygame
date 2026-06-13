<script lang="ts">
	import { messages } from '$lib/i18n';
	import { formatRevealValue } from '$lib/reveal-format';

	interface HostReviewQueueProps {
		activeStep?: RuntimeStepState;
		buzzedPlayerId?: string;
		customScore: number;
		disabledBuzzerPlayerIds: string[];
		hostAnswer?: RevealedAnswer;
		playerMap: Map<string, Player>;
		submissions: SubmissionItem[];
		isSubmissionReviewed: (playerId: string) => boolean;
		onRevealSubmission: (playerId?: string) => void;
		onReviewSubmission: (playerId: string, accepted: boolean, pointsOverride?: number) => void;
	}

	let {
		activeStep,
		buzzedPlayerId,
		customScore,
		disabledBuzzerPlayerIds,
		hostAnswer,
		playerMap,
		submissions,
		isSubmissionReviewed,
		onRevealSubmission,
		onReviewSubmission
	}: HostReviewQueueProps = $props();

	function playerName(playerId?: string): string {
		if (!playerId) {
			return '';
		}
		return playerMap.get(playerId)?.name ?? playerId;
	}
</script>

<section class="card controller-compact-card host-review-card stack-md">
	<h2 class="label-title text-2xl">{$messages.gameplay.reviewQueue}</h2>
	{#if hostAnswer}
		<div class="host-review-item theme-soft-correct rounded-2xl border px-4 py-3">
			<p class="theme-soft-correct-label text-sm font-black uppercase tracking-[0.18em]">
				{$messages.common.correctAnswer}
			</p>
			<p class="mt-2 text-lg font-extrabold leading-tight">
				{formatRevealValue(hostAnswer.value)}
			</p>
		</div>
	{/if}
	{#if activeStep?.input_kind === 'buzzer' && buzzedPlayerId}
		<div class="host-review-item theme-surface-muted rounded-2xl border p-3">
			<p class="theme-text font-bold">{playerName(buzzedPlayerId)}</p>
			<p class="theme-text-muted mt-1">{$messages.gameplay.buzzedInFirst}</p>
			<div class="mt-3 flex flex-wrap gap-2">
				{#if isSubmissionReviewed(buzzedPlayerId)}
					<span class="host-reviewed-badge badge">{$messages.gameplay.reviewed}</span>
				{:else}
					<button
						type="button"
						class="btn btn-primary"
						onclick={() => onReviewSubmission(buzzedPlayerId, true, activeStep?.evaluation_points)}
					>
						{$messages.gameplay.acceptWithPoints(activeStep?.evaluation_points ?? 1)}
					</button>
					<button
						type="button"
						class="btn btn-danger"
						onclick={() => onReviewSubmission(buzzedPlayerId, false)}
					>
						{$messages.gameplay.reject}
					</button>
				{/if}
			</div>
		</div>
	{:else if submissions.length === 0}
		{#if activeStep?.input_kind === 'buzzer' && disabledBuzzerPlayerIds.length > 0}
			<p class="theme-text-muted">
				{$messages.gameplay.waitingToReactivateBuzzers}
				{$messages.gameplay.lockedOut}:
				{disabledBuzzerPlayerIds.map((playerId) => playerName(playerId)).join(', ')}
			</p>
		{:else}
			<p class="theme-text-muted">{$messages.gameplay.noAnswersSubmittedYet}</p>
		{/if}
	{:else}
		{#each submissions as submission}
			<div
				class={`host-review-item rounded-2xl border p-3 ${
					isSubmissionReviewed(submission.player_id)
						? 'theme-surface-muted opacity-70'
						: 'theme-surface-muted'
				}`}
			>
				<p class="theme-text font-bold">{playerName(submission.player_id)}</p>
				<p class="mt-1 wrap-break-word">{formatRevealValue(submission.value)}</p>
				<div class="mt-3 flex flex-wrap gap-2">
					<button
						type="button"
						class="btn btn-ghost"
						onclick={() => onRevealSubmission(submission.player_id)}
						disabled={isSubmissionReviewed(submission.player_id)}
					>
						{$messages.gameplay.reveal}
					</button>
					{#if !isSubmissionReviewed(submission.player_id)}
						<button
							type="button"
							class="btn btn-primary"
							onclick={() =>
								onReviewSubmission(submission.player_id, true, activeStep?.evaluation_points)}
						>
							{$messages.gameplay.acceptWithPoints(activeStep?.evaluation_points ?? 1)}
						</button>
						<button
							type="button"
							class="btn btn-danger"
							onclick={() => onReviewSubmission(submission.player_id, false)}
						>
							{$messages.gameplay.reject}
						</button>
						{#if customScore !== 0}
							<button
								type="button"
								class="btn btn-ghost"
								onclick={() => onReviewSubmission(submission.player_id, true, customScore)}
							>
								{$messages.gameplay.acceptCustomPoints(customScore)}
							</button>
						{/if}
					{:else}
						<span class="host-reviewed-badge badge">{$messages.gameplay.reviewed}</span>
					{/if}
				</div>
			</div>
		{/each}
	{/if}
</section>

<style>
	@media (max-width: 640px) {
		.host-review-card {
			gap: 0.6rem;
		}

		.host-review-item {
			border-radius: 0.85rem;
			padding: 0.65rem;
		}

		.host-review-item :global(.btn) {
			border-radius: 0.85rem;
			padding: 0.65rem 0.8rem;
			font-size: 1rem;
			line-height: 1.1;
		}
	}

	.host-reviewed-badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-height: 2.75rem;
		border: 1px solid var(--party-border);
		background: var(--party-muted-control);
		color: var(--party-ink);
		line-height: 1;
	}
</style>
