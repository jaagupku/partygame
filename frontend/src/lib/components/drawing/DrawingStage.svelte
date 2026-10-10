<script lang="ts">
	import { onMount } from 'svelte';
	import DrawingDisplay from '$lib/components/DrawingDisplay.svelte';
	import { messages } from '$lib/i18n';
	import { drawingText } from './helpers';
	import DrawingCriterion from './DrawingCriterion.svelte';
	import DrawingResults from './DrawingResults.svelte';
	import PromptCountdown from './PromptCountdown.svelte';
	import { INTRO_SECONDS, drawingSegment, isIntroPhase, serverRemaining } from './reveal';
	let {
		view,
		mainDisplay = false,
		oncue
	}: {
		view: DrawingGameView;
		mainDisplay?: boolean;
		/** Shared display only: live countdown and results milestones, keyed per phase. */
		oncue?: (name: string, key: string) => void;
	} = $props();
	const prominentTimer = $derived(
		mainDisplay && (view.phase === 'writing' || view.phase === 'drawing')
	);
	const intro = $derived(isIntroPhase(view.phase));
	let now = $state(Date.now() / 1000);
	onMount(() => {
		const timer = setInterval(() => (now = Date.now() / 1000), 200);
		return () => clearInterval(timer);
	});
	const seconds = $derived(
		Math.max(
			0,
			Math.ceil(view.paused ? (view.remaining_seconds ?? 0) : (view.deadline ?? now) - now)
		)
	);
	const segment = $derived(drawingSegment(view, seconds));
	// The nudge to switch drawings stays up briefly, then settles into a plain position label.
	const moveOn = $derived(!!segment && segment.index > 0 && segment.into < 10);
	const phaseTitle = $derived(
		view.phase === 'criterion_reveal'
			? $messages.drawingMashup.criterionReveal
			: ($messages.drawingMashup[
					view.phase as 'writing' | 'drawing' | 'showcase' | 'voting' | 'results'
				] ?? '')
	);
	const introTotal = $derived(isIntroPhase(view.phase) ? INTRO_SECONDS[view.phase] : 0);
	const introLeft = $derived(Math.min(introTotal, serverRemaining(view)));

	// Warnings only follow a countdown seen live, so reconnecting near the end stays quiet.
	let watchedPhase = -1;
	let lowest = Infinity;
	$effect(() => {
		const left = seconds;
		if (!oncue || view.paused || !['writing', 'drawing', 'voting'].includes(view.phase)) return;
		if (watchedPhase !== view.phase_id) {
			watchedPhase = view.phase_id;
			lowest = left;
			return;
		}
		for (const mark of [5, 3, 2, 1])
			if (left <= mark && mark < lowest)
				oncue(mark === 5 ? 'timerWarning' : 'timerTick', `${view.phase_id}:countdown:${mark}`);
		lowest = Math.min(lowest, left);
	});
	let watchedSegment = '';
	$effect(() => {
		const current = segment ? `${view.phase_id}:${segment.index}` : '';
		if (oncue && moveOn && !view.paused && watchedSegment && current !== watchedSegment)
			oncue('timerWarning', `${view.phase_id}:segment:${segment!.index}`);
		watchedSegment = current;
	});
</script>

<section
	class="stack-md drawing-stage"
	class:writing-display={prominentTimer}
	class:main-display={mainDisplay}
	class:fit={mainDisplay && !!view.matchup && !prominentTimer}
	class:drawing-stage-paused={view.paused}
	data-drawing-stage={view.phase}
>
	<header class="flex flex-wrap items-center justify-between gap-4">
		<h2 class="drawing-phase-title text-2xl font-bold">{phaseTitle}</h2>
		{#if intro}
			<div class="drawing-intro-clock">
				<span
					>{view.paused ? $messages.drawingMashup.paused : $messages.drawingMashup.votingSoon}</span
				>
				<!-- Restart from the authoritative position whenever a new snapshot arrives. -->
				{#key `${view.phase_id}:${view.paused}:${view.deadline}:${view.server_time}`}
					<span
						class="drawing-intro-progress"
						role="progressbar"
						aria-label={$messages.drawingMashup.introProgress}
						aria-valuemin="0"
						aria-valuemax={introTotal}
						aria-valuenow={Math.round(introTotal - introLeft)}
						><span
							style:--intro-from={introTotal ? 1 - introLeft / introTotal : 1}
							style:--intro-duration={`${introLeft}s`}
							style:--intro-steps={introTotal}
						></span></span
					>
				{/key}
			</div>
		{:else if view.phase !== 'results' && !prominentTimer}<p class="text-xl font-bold">
				{view.paused
					? $messages.drawingMashup.paused
					: `${$messages.drawingMashup.timeLeft}: ${seconds}s`}
			</p>{/if}
	</header>
	{#if prominentTimer}
		<div class="writing-countdown">
			{#key view.phase_id}<PromptCountdown {seconds} paused={view.paused} />{/key}
		</div>
		<div class="writing-status">
			{#if segment}
				{#key `${segment.index}:${moveOn}`}
					<p class="drawing-segment" class:drawing-move-on={moveOn} role="status">
						{moveOn
							? $messages.drawingMashup.moveOn(segment.index + 1)
							: $messages.drawingMashup.drawingOf(segment.index + 1, segment.count)}
					</p>
				{/key}
			{/if}
			<p class="text-xl">{$messages.drawingMashup.waiting}</p>
			<p class="theme-text-muted">
				{$messages.drawingMashup.progress}: {view.ready_ids.length} / {view.participant_ids.length}
			</p>
		</div>
	{:else if view.matchup}
		<p class="theme-text-muted">{view.matchup_number} / {view.matchup_count}</p>
		<div class="drawing-brief">
			<div class="drawing-topic">
				<span class="drawing-topic-label">{$messages.drawingMashup.topic}</span>
				<h3 class="text-3xl font-black">
					{drawingText(view.matchup.topic, 'topic', view.language)}
				</h3>
			</div>
			<DrawingCriterion {view} />
		</div>
		{#if view.phase === 'results'}
			{#key `${view.matchup.id}:${view.phase_id}`}<DrawingResults
					{view}
					{oncue}
					fit={mainDisplay}
				/>{/key}
		{:else}
			<!-- The artwork stays put while the stage around it transforms. -->
			<div class="drawing-artworks" style:--columns={Math.max(1, view.matchup.drawings.length)}>
				{#each view.matchup.drawings as artwork, i (artwork.id)}
					<article class="drawing-artwork card stack-sm min-w-0">
						<p class="font-bold">{String.fromCharCode(65 + i)}</p>
						<div class="art-frame"><DrawingDisplay drawing={artwork.value} /></div>
					</article>
				{/each}
			</div>
		{/if}
	{:else}
		<p class="text-xl">{$messages.drawingMashup.waiting}</p>
		{#if view.phase === 'drawing'}<p>{$messages.drawingMashup.criterionHidden}</p>{/if}
	{/if}
	{#if view.phase !== 'results' && !prominentTimer && !intro}<p class="theme-text-muted">
			{$messages.drawingMashup.progress}: {view.ready_ids.length} / {view.participant_ids.length}
		</p>{/if}
</section>

<style>
	.drawing-stage {
		padding: 1rem;
		overflow: auto;
		max-height: 100%;
	}
	/* Room for the waiting-player rail along the left edge of the shared display. */
	.main-display {
		padding-left: 4.5rem;
	}
	/* The centred countdown stays centred on the screen, not just the free space. */
	.main-display.writing-display {
		padding-right: 4.5rem;
	}
	/* The shared display cannot scroll: artwork shrinks so every card stays on screen. */
	.fit {
		height: 100%;
	}
	.drawing-artworks {
		display: grid;
		gap: 1rem;
	}
	@media (min-width: 768px) {
		.drawing-artworks {
			grid-template-columns: repeat(var(--columns), minmax(0, 1fr));
		}
	}
	.main-display .drawing-artworks {
		grid-template-columns: repeat(var(--columns), minmax(0, 1fr));
	}
	.art-frame :global(.drawing-display) {
		width: min(100%, calc(55dvh * var(--drawing-aspect, 4 / 3)));
		margin-inline: auto;
	}
	.fit > .drawing-artworks {
		gap: 0.75rem;
		flex: 1 1 0;
		min-height: 0;
		grid-template-rows: minmax(0, 1fr);
	}
	/* Artwork is width-bound on wide screens, so the frame around it stays slim. */
	.fit .drawing-artwork {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		min-height: 0;
		padding: 0.5rem;
	}
	.fit .art-frame {
		flex: 1 1 0;
		min-height: 6rem;
		container-type: size;
		display: grid;
		align-content: center;
	}
	.fit .art-frame :global(.drawing-display) {
		width: min(100cqw, calc(100cqh * var(--drawing-aspect, 4 / 3)));
		margin-inline: auto;
	}
	.drawing-segment {
		font-size: clamp(1.4rem, 2.6vw, 2.2rem);
		font-weight: 900;
	}
	.drawing-move-on {
		color: var(--party-accent-strong);
		animation: drawing-move-on 700ms cubic-bezier(0.2, 1.6, 0.4, 1) both;
	}
	@keyframes drawing-move-on {
		from {
			transform: scale(0.6);
			opacity: 0;
		}
	}
	.writing-display {
		display: grid;
		grid-template-rows: minmax(min-content, 1fr) auto minmax(min-content, 1fr);
		height: 100%;
		text-align: center;
		gap: 1rem;
	}
	.writing-display > header {
		justify-content: center;
		align-self: start;
	}
	.writing-countdown {
		margin: 0;
	}
	.writing-status {
		align-self: end;
		display: grid;
		gap: 0.5rem;
	}
	.drawing-brief {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr));
		align-items: start;
		gap: 1rem;
	}
	.drawing-topic {
		display: grid;
		gap: 0.2rem;
		min-width: 0;
		overflow-wrap: anywhere;
	}
	.drawing-topic-label {
		font-size: 0.8rem;
		font-weight: 800;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		opacity: 0.75;
	}
	.drawing-intro-clock {
		display: grid;
		justify-items: end;
		gap: 0.35rem;
		font-weight: 800;
	}
	.drawing-intro-progress {
		display: block;
		width: min(14rem, 50vw);
		height: 0.6rem;
		border-radius: 999px;
		background: var(--party-border);
		overflow: hidden;
	}
	.drawing-intro-progress > span {
		display: block;
		height: 100%;
		background: var(--party-accent);
		transform-origin: left;
		transform: scaleX(var(--intro-from));
		animation: drawing-intro-fill var(--intro-duration) linear forwards;
	}
	.drawing-stage-paused .drawing-intro-progress > span {
		animation: none;
	}
	@keyframes drawing-intro-fill {
		from {
			transform: scaleX(var(--intro-from));
		}
		to {
			transform: scaleX(1);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.drawing-move-on {
			animation: none;
		}
		/* The same timing, in whole-second steps rather than continuous movement. */
		.drawing-intro-progress > span {
			animation-timing-function: steps(var(--intro-steps), end);
		}
	}
</style>
