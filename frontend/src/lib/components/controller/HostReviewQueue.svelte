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

<section class="card stack-md">
	<h2 class="label-title text-2xl">{$messages.gameplay.reviewQueue}</h2>
	{#if hostAnswer}
		<div class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3">
			<p class="text-sm font-black uppercase tracking-[0.18em] text-emerald-700">
				{$messages.common.correctAnswer}
			</p>
			<p class="mt-2 text-lg font-extrabold leading-tight text-slate-950">
				{formatRevealValue(hostAnswer.value)}
			</p>
		</div>
	{/if}
	{#if activeStep?.input_kind === 'buzzer' && buzzedPlayerId}
		<div class="rounded-2xl bg-white/70 p-3">
			<p class="font-bold">{playerName(buzzedPlayerId)}</p>
			<p class="mt-1 text-slate-600">{$messages.gameplay.buzzedInFirst}</p>
			<div class="mt-3 flex flex-wrap gap-2">
				{#if isSubmissionReviewed(buzzedPlayerId)}
					<span class="badge bg-slate-200 text-slate-700">{$messages.gameplay.reviewed}</span>
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
			<p class="text-slate-500">
				{$messages.gameplay.waitingToReactivateBuzzers}
				{$messages.gameplay.lockedOut}:
				{disabledBuzzerPlayerIds.map((playerId) => playerName(playerId)).join(', ')}
			</p>
		{:else}
			<p class="text-slate-500">{$messages.gameplay.noAnswersSubmittedYet}</p>
		{/if}
	{:else}
		{#each submissions as submission}
			<div
				class={`rounded-2xl p-3 ${
					isSubmissionReviewed(submission.player_id) ? 'bg-slate-100 opacity-70' : 'bg-white/70'
				}`}
			>
				<p class="font-bold">{playerName(submission.player_id)}</p>
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
						<span class="badge bg-slate-200 text-slate-700">{$messages.gameplay.reviewed}</span>
					{/if}
				</div>
			</div>
		{/each}
	{/if}
</section>
