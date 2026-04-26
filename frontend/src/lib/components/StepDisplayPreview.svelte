<script lang="ts">
	import GameConnectionStatus from '$lib/components/GameConnectionStatus.svelte';
	import QuestionCard from '$lib/components/QuestionCard.svelte';
	import Timer from '$lib/components/util/Timer.svelte';
	import { messages } from '$lib/i18n';
	import { formatRevealValue } from '$lib/reveal-format';

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
		connected = null
	}: StepDisplayPreviewProps = $props();

	const stageLayout = $derived(layoutMode === 'host-stage');
	const showingAnswerReveal = $derived(displayPhase === 'answer_reveal');
</script>

<div
	class={`mt-0 ${stageLayout ? 'grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-2 overflow-hidden' : 'stack-lg'}`}
>
	<div>
		<GameConnectionStatus {connected} {connectionLabel} showInline={false} {showDisconnectedChip} />
	</div>

	<QuestionCard
		{step}
		{revealedSubmission}
		{revealedAnswer}
		{buzzerActive}
		{buzzedPlayerName}
		{displayPhase}
		variant={stageLayout ? 'stage' : 'default'}
	/>

	{#if stageLayout && showingAnswerReveal && revealedAnswer}
		<div class="card w-full border-emerald-200 bg-emerald-50 p-4 md:p-5">
			<p class="text-center text-sm font-black uppercase tracking-[0.22em] text-emerald-700">
				{$messages.common.correctAnswer}
			</p>
			<p
				class="mt-3 text-center text-[clamp(1.4rem,3vw,2.6rem)] font-extrabold leading-tight text-slate-950"
			>
				{formatRevealValue(revealedAnswer.value)}
			</p>
		</div>
	{:else if countdown > 0 && !showingAnswerReveal}
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
	{/if}
</div>
