<script lang="ts">
	import GameConnectionStatus from '$lib/components/GameConnectionStatus.svelte';
	import DrawingDisplay from '$lib/components/DrawingDisplay.svelte';
	import MapPointEditor from '$lib/components/MapPointEditor.svelte';
	import QuestionCard from '$lib/components/QuestionCard.svelte';
	import Timer from '$lib/components/util/Timer.svelte';
	import { DEFAULT_AVATAR_PRESET_KEY } from '$lib/avatar-presets';
	import { getDrawingVoteRubric } from '$lib/drawing-vote.js';
	import { messages } from '$lib/i18n';
	import { formatRevealValue, isOptionRevealStep, isOrderingRevealStep } from '$lib/reveal-format';
	import { onDestroy } from 'svelte';

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
		drawingItems?: DrawingVoteItem[];
		drawingVoteCount?: number;
		players?: Player[];
		submissions?: SubmissionItem[];
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
		submissionCount = 0,
		drawingItems = [],
		drawingVoteCount = 0,
		players = [],
		submissions = []
	}: StepDisplayPreviewProps = $props();

	let lastSubmissionCount = $state(0);
	let hasSeenSubmissionCount = $state(false);
	let submissionPulseKey = $state(0);
	let mapRevealMarkersVisible = $state(false);
	let mapRevealTimer: number | null = null;

	const stageLayout = $derived(layoutMode === 'host-stage');
	const showingAnswerReveal = $derived(displayPhase === 'answer_reveal');
	const mapRevealStep = $derived(
		step?.input_kind === 'map' && step?.evaluation_type === 'map_distance'
	);
	const drawingStep = $derived(
		step?.input_kind === 'drawing' && step?.evaluation_type === 'favorite_vote'
	);
	const drawingVoteRubric = $derived(getDrawingVoteRubric(step));
	const showStageRevealCard = $derived(
		stageLayout &&
			showingAnswerReveal &&
			revealedAnswer &&
			!mapRevealStep &&
			!isOptionRevealStep(step) &&
			!isOrderingRevealStep(step)
	);
	const showSubmissionIndicator = $derived(
		stageLayout && submissionCount > 0 && !showingAnswerReveal
	);
	const showBuzzerWinner = $derived(stageLayout && Boolean(buzzedPlayerName));
	const playerMap = $derived(new Map(players.map((player) => [player.id, player])));
	const correctMapPoint = $derived(getCorrectMapPoint(revealedAnswer));
	const mapScoringAnswer = $derived(getMapScoringAnswer(revealedAnswer));
	const mapGuessMarkers = $derived(
		submissions
			.map((submission) => {
				const point = getMapPoint(submission.value);
				const player = playerMap.get(submission.player_id);
				if (!point || !player) {
					return null;
				}
				return {
					id: submission.player_id,
					name: player.name,
					point,
					avatarKind: player.avatar_kind ?? 'preset',
					avatarPresetKey: player.avatar_preset_key ?? DEFAULT_AVATAR_PRESET_KEY,
					avatarUrl: player.avatar_url ?? null
				};
			})
			.filter((marker): marker is NonNullable<typeof marker> => marker !== null)
	);

	$effect(() => {
		if (hasSeenSubmissionCount && submissionCount > lastSubmissionCount) {
			submissionPulseKey += 1;
		}
		lastSubmissionCount = submissionCount;
		hasSeenSubmissionCount = true;
	});

	$effect(() => {
		if (mapRevealTimer !== null) {
			clearTimeout(mapRevealTimer);
			mapRevealTimer = null;
		}
		mapRevealMarkersVisible = false;
		if (!showingAnswerReveal || !mapRevealStep) {
			return;
		}
		mapRevealTimer = window.setTimeout(() => {
			mapRevealMarkersVisible = true;
			mapRevealTimer = null;
		}, 1000);
	});

	onDestroy(() => {
		if (mapRevealTimer !== null) {
			clearTimeout(mapRevealTimer);
		}
	});

	function getMapPoint(value: unknown): MapPoint | null {
		if (typeof value === 'string') {
			try {
				return getMapPoint(JSON.parse(value));
			} catch {
				return null;
			}
		}
		if (!value || typeof value !== 'object') {
			return null;
		}
		const point = value as Partial<MapPoint>;
		const lat = Number(point.lat);
		const lng = Number(point.lng);
		if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
			return null;
		}
		return { lat, lng };
	}

	function getCorrectMapPoint(answer?: RevealedAnswer): MapPoint | null {
		return getMapScoringAnswer(answer)?.correct_point ?? null;
	}

	function getMapScoringAnswer(answer?: RevealedAnswer): MapDistanceAnswer | null {
		if (!answer?.value || typeof answer.value !== 'object') {
			return null;
		}
		const value = answer.value as Partial<MapDistanceAnswer>;
		const correctPoint = getMapPoint(value.correct_point);
		if (!correctPoint) {
			return null;
		}
		return {
			correct_point: correctPoint,
			scoring_mode: value.scoring_mode ?? 'bands',
			max_points: Number(value.max_points ?? 0),
			zero_distance_m: value.zero_distance_m ?? null,
			full_credit_distance_m: value.full_credit_distance_m ?? null,
			bands: Array.isArray(value.bands) ? value.bands : []
		};
	}
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

	{#if drawingStep && (displayPhase === 'drawing_vote' || showingAnswerReveal)}
		<section class="drawing-reveal-stage question-stage-enter">
			<div class="question-card-title-row">
				<h3
					class="question-card-step-title text-[clamp(1.8rem,3.4vw,3.6rem)] font-extrabold leading-tight"
				>
					{step?.title}
				</h3>
				<span class="question-card-points-badge points-badge-stage">
					{showingAnswerReveal
						? `${$messages.gameplay.votesLabel}: ${drawingVoteCount}`
						: $messages.gameplay.voteNow}
				</span>
			</div>
			{#if displayPhase === 'drawing_vote' && drawingVoteRubric}
				<div class="drawing-vote-rubric">
					<p>{$messages.gameplay.drawingVoteRubric}</p>
					<strong>{drawingVoteRubric}</strong>
				</div>
			{/if}
			<div class="drawing-gallery">
				{#each drawingItems as item}
					<article class="drawing-gallery-item">
						<DrawingDisplay
							drawing={item.value}
							className="drawing-gallery-canvas"
							animate={stageLayout}
							durationMs={1500}
							replayKey={`${displayPhase}:${item.id}`}
						/>
						<div class="drawing-gallery-caption">
							<span>{showingAnswerReveal ? (item.player_name ?? item.label) : item.label}</span>
							{#if showingAnswerReveal}
								<span>
									{item.vote_count}
									{$messages.gameplay.votesLabel.toLowerCase()} · +{item.points_awarded}
								</span>
							{/if}
						</div>
					</article>
				{/each}
			</div>
		</section>
	{:else if showingAnswerReveal && mapRevealStep && step?.map}
		<section class="map-reveal-stage question-stage-enter">
			<div class="question-card-title-row">
				<h3
					class="question-card-step-title text-[clamp(1.8rem,3.4vw,3.6rem)] font-extrabold leading-tight"
				>
					{step.title}
				</h3>
				<span class="question-card-points-badge points-badge-stage">
					{step.max_points ?? step.evaluation_points}
					{$messages.common.pointsWord}
				</span>
			</div>
			<MapPointEditor
				mode="reveal"
				mapConfig={step.map}
				baseLayer="osm"
				correctPoint={correctMapPoint}
				scoringAnswer={mapRevealMarkersVisible ? mapScoringAnswer : null}
				guessMarkers={mapGuessMarkers}
				showCorrect={mapRevealMarkersVisible}
				showGuesses={mapRevealMarkersVisible}
				showLines={mapRevealMarkersVisible}
				fitRevealToGuesses={mapRevealMarkersVisible}
				guessLabelMode="hover"
				heightClass="h-full"
			/>
		</section>
	{:else}
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
	{/if}

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
		height: 100%;
		min-height: 0;
		min-width: 0;
		overflow: hidden;
		animation: question-enter 360ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
	}

	.map-reveal-stage {
		display: grid;
		grid-template-rows: auto minmax(0, 1fr);
		gap: clamp(0.5rem, 1.2vh, 1rem);
		height: 100%;
		min-height: 0;
		min-width: 0;
		padding: clamp(0.5rem, 1.1vw, 1.25rem);
	}

	.drawing-reveal-stage {
		display: grid;
		grid-template-rows: auto auto minmax(0, 1fr);
		gap: clamp(0.5rem, 1.2vh, 1rem);
		height: 100%;
		min-height: 0;
		min-width: 0;
		padding: clamp(0.5rem, 1.1vw, 1.25rem);
	}

	.drawing-gallery {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(13rem, 100%), min(24rem, 100%)));
		align-content: center;
		justify-content: center;
		gap: clamp(0.65rem, 1.5vw, 1.2rem);
		min-height: 0;
		overflow: hidden;
	}

	.drawing-vote-rubric {
		display: grid;
		gap: 0.25rem;
		border: 1px solid rgb(191 219 254 / 0.85);
		border-radius: 0.75rem;
		background: rgb(239 246 255 / 0.9);
		padding: clamp(0.65rem, 1.1vw, 0.95rem);
		color: rgb(15 23 42);
	}

	.drawing-vote-rubric p {
		font-size: clamp(0.7rem, 0.9vw, 0.85rem);
		font-weight: 950;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: rgb(30 64 175);
	}

	.drawing-vote-rubric strong {
		font-size: clamp(1rem, 1.45vw, 1.35rem);
		line-height: 1.2;
		overflow-wrap: anywhere;
	}

	.drawing-gallery-item {
		display: grid;
		gap: 0.5rem;
		min-width: 0;
		border: 1px solid rgb(203 213 225 / 0.9);
		border-radius: 1rem;
		background: rgb(248 250 252 / 0.9);
		padding: clamp(0.55rem, 1vw, 0.85rem);
		box-shadow: 0 8px 20px rgb(15 23 42 / 0.1);
	}

	:global(.drawing-gallery-canvas) {
		border: 3px solid rgb(255 255 255);
		outline: 1px solid rgb(148 163 184 / 0.72);
		box-shadow:
			inset 0 0 0 1px rgb(15 23 42 / 0.05),
			0 1px 3px rgb(15 23 42 / 0.14);
	}

	.drawing-gallery-caption {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		font-size: clamp(0.82rem, 1.15vw, 1rem);
		font-weight: 950;
		color: rgb(15 23 42);
	}

	.question-card-title-row {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: clamp(0.75rem, 2vw, 1.5rem);
		min-width: 0;
	}

	.question-card-step-title {
		min-width: 0;
		overflow-wrap: anywhere;
	}

	.question-card-points-badge {
		flex: 0 0 auto;
		margin-top: 0.15rem;
		border-radius: 999px;
		background: rgb(255 255 255 / 0.88);
		padding: 0.45rem 0.8rem;
		font-size: 0.78rem;
		font-weight: 900;
		text-transform: uppercase;
		color: rgb(15 23 42);
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
