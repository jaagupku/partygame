<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import DrawingDisplay from '$lib/components/DrawingDisplay.svelte';
	import { messages } from '$lib/i18n';
	import { revealElapsed, revealStep, voteStartsAt } from './reveal';

	let { view }: { view: DrawingGameView } = $props();
	let elapsed = $state(0);
	let reducedMotion = $state(false);
	const matchup = $derived(view.matchup!);
	const duration = $derived(view.reveal_duration ?? 12);
	const legacy = $derived(view.reveal_duration == null || view.server_time == null);
	const step = $derived(revealStep(legacy ? Infinity : elapsed, duration, reducedMotion));
	const votes = $derived(
		(matchup.revealed_votes ?? []).map((vote, index, all) => ({
			...vote,
			startsAt: voteStartsAt(index, all.length, duration)
		}))
	);
	const highest = $derived(Math.max(0, ...matchup.drawings.map((art) => art.points)));
	const allocation = $derived(
		matchup.allocation === 'votes'
			? $messages.drawingMashup.allocationVotes
			: matchup.allocation
				? $messages.drawingMashup[matchup.allocation]
				: ''
	);

	$effect(() => {
		const snapshotElapsed = revealElapsed(view);
		const paused = view.paused;
		const total = view.reveal_duration ?? 12;
		// A pause is an authoritative position shared by every screen, including reloads.
		const anchor = paused
			? snapshotElapsed
			: Math.max(
					snapshotElapsed,
					untrack(() => elapsed)
				);
		const receivedAt = performance.now();
		elapsed = anchor;
		if (paused || !Number.isFinite(anchor)) return;
		let frame: number;
		function tick() {
			elapsed = Math.min(total, anchor + (performance.now() - receivedAt) / 1000);
			if (elapsed < total) frame = requestAnimationFrame(tick);
		}
		frame = requestAnimationFrame(tick);
		return () => cancelAnimationFrame(frame);
	});

	onMount(() => {
		const query = window.matchMedia('(prefers-reduced-motion: reduce)');
		const update = () => (reducedMotion = query.matches);
		update();
		query.addEventListener('change', update);
		return () => query.removeEventListener('change', update);
	});
</script>

<div class="results stack-md" class:reduced-motion={reducedMotion} data-reveal-stage={step.stage}>
	<div class="reveal-heading">
		<p class="reveal-label" role="status" aria-live="polite" aria-atomic="true">
			{$messages.drawingMashup[step.stage]}
		</p>
		{#if view.paused}
			<span>{$messages.drawingMashup.paused}</span>
		{:else if !legacy}
			<span class="theme-text-muted">
				{$messages.drawingMashup.timeLeft}: {Math.max(0, Math.ceil(duration - elapsed))}s
			</span>
		{/if}
	</div>
	<div class="grid gap-4 md:grid-cols-3">
		{#each matchup.drawings as artwork, i (artwork.id)}
			{@const artworkVotes = votes.filter((vote) => vote.drawing_id === artwork.id)}
			{@const arrived = artworkVotes.filter((vote) => elapsed >= vote.startsAt + 0.35)}
			{@const winner = step.pointsVisible && artwork.points === highest && highest > 0}
			<article
				class="card artwork stack-sm"
				class:winner
				data-artwork-id={artwork.id}
				style:--art-color={['#8b5cf6', '#0d9488', '#d97706'][i % 3]}
			>
				<div class="artist-heading" style:animation-delay={`-${Math.min(1, elapsed)}s`}>
					<span class="art-letter">{String.fromCharCode(65 + i)}</span>
					<strong class="artist-name">{artwork.player_name}</strong>
				</div>
				<DrawingDisplay drawing={artwork.value} />
				<div class="vote-heading">
					<span
						>{$messages.drawingMashup.voteCount(legacy ? artwork.vote_count : arrived.length)}</span
					>
					{#if winner}<span class="winner-label">{$messages.drawingMashup.topDrawing}</span>{/if}
				</div>
				<ul
					class="voter-list"
					aria-label={$messages.drawingMashup.votedForDrawing(artwork.player_name ?? '')}
				>
					{#each artworkVotes as vote (vote.voter_id)}
						{#if elapsed >= vote.startsAt}
							<li
								class="voter"
								data-voter-id={vote.voter_id}
								style:animation-delay={`-${Math.min(1, Math.max(0, elapsed - vote.startsAt))}s`}
							>
								<span aria-hidden="true">↗</span>
								{vote.voter_name}
							</li>
						{/if}
					{/each}
				</ul>
				<div class="award" class:concealed={!step.pointsVisible} aria-hidden={!step.pointsVisible}>
					<div class="point-bar" aria-hidden="true">
						<span style:width={`${(artwork.points / 10) * step.pointsProgress}%`}></span>
					</div>
					<p class="point-total" data-award={artwork.id}>
						+{Math.round(artwork.points * step.pointsProgress)}
						<span>{$messages.drawingMashup.points}</span>
					</p>
					<p class="theme-text-muted">{$messages.drawingMashup.pointShare(artwork.points / 10)}</p>
				</div>
			</article>
		{/each}
	</div>
	<div class="allocation" class:concealed={!step.pointsVisible} aria-hidden={!step.pointsVisible}>
		<p>{allocation}</p>
		{#if matchup.drawings.length}
			<div class="pool-bar" aria-hidden="true">
				{#each matchup.drawings as artwork, i (artwork.id)}
					<span
						style:width={`${(artwork.points / 10) * step.pointsProgress}%`}
						style:background={['#8b5cf6', '#0d9488', '#d97706'][i % 3]}
					></span>
				{/each}
			</div>
		{/if}
	</div>
	<div class="bonuses" class:concealed={!step.bonusesVisible} aria-hidden={!step.bonusesVisible}>
		{#each ['topic', 'criterion'] as kind}
			{@const author = kind === 'topic' ? matchup.topic_author : matchup.criterion_author}
			{@const points = kind === 'topic' ? matchup.topic_points : matchup.criterion_points}
			{#if author}
				<div
					class="bonus theme-soft-primary"
					style:animation-delay={`-${Math.min(1, Math.max(0, elapsed - (duration - 6.5)))}s`}
				>
					<span class="theme-text-muted"
						>{kind === 'topic'
							? $messages.drawingMashup.topic
							: $messages.drawingMashup.criterion}</span
					>
					<strong>{author}</strong>
					<span>{$messages.drawingMashup.bonusBreakdown(points / 10, points)}</span>
				</div>
			{/if}
		{/each}
	</div>
</div>

<style>
	.results {
		min-width: 0;
	}
	.reveal-heading,
	.artist-heading,
	.vote-heading {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		flex-wrap: wrap;
	}
	.reveal-label {
		font-size: 1.15rem;
		font-weight: 800;
	}
	.artwork {
		min-width: 0;
		border: 2px solid transparent;
		position: relative;
	}
	.artwork.winner {
		border-color: var(--art-color);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--art-color) 18%, transparent);
	}
	.artist-heading {
		justify-content: flex-start;
		animation: name-reveal 0.6s both paused;
	}
	.art-letter {
		display: grid;
		place-items: center;
		width: 2rem;
		height: 2rem;
		border-radius: 50%;
		background: var(--art-color);
		color: white;
		font-weight: 900;
	}
	.artist-name {
		overflow-wrap: anywhere;
		flex: 1;
	}
	.winner-label {
		color: var(--art-color);
		font-size: 0.8rem;
		font-weight: 800;
	}
	.voter-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		min-height: 2.3rem;
		padding: 0;
		margin: 0;
		list-style: none;
	}
	.voter {
		align-self: flex-start;
		max-width: 100%;
		overflow-wrap: anywhere;
		border-radius: 999px;
		padding: 0.35rem 0.7rem;
		font-size: 0.85rem;
		font-weight: 700;
		background: color-mix(in srgb, var(--art-color) 16%, transparent);
		animation: vote-land 0.35s both paused;
	}
	.point-bar,
	.pool-bar {
		height: 0.6rem;
		overflow: hidden;
		border-radius: 999px;
		background: color-mix(in srgb, var(--art-color, #8b5cf6) 12%, transparent);
	}
	.point-bar span {
		display: block;
		height: 100%;
		background: var(--art-color);
	}
	.pool-bar {
		display: flex;
		margin-top: 0.65rem;
		height: 0.8rem;
	}
	.point-total {
		font-size: clamp(1.8rem, 3vw, 3rem);
		font-weight: 900;
		font-variant-numeric: tabular-nums;
		margin: 0.35rem 0 0;
	}
	.point-total span {
		font-size: 0.9rem;
		font-weight: 600;
	}
	.award .theme-text-muted {
		font-size: 0.8rem;
	}
	.concealed {
		visibility: hidden;
	}
	.allocation {
		text-align: center;
		font-weight: 600;
	}
	.bonuses {
		display: flex;
		gap: 0.75rem;
		flex-wrap: wrap;
	}
	.bonus {
		flex: 1 1 12rem;
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		padding: 0.8rem 1rem;
		border-radius: 0.8rem;
		overflow-wrap: anywhere;
		animation: name-reveal 0.5s both paused;
	}
	.bonus .theme-text-muted {
		font-size: 0.8rem;
	}
	@keyframes vote-land {
		from {
			opacity: 0;
			transform: translateY(-1.5rem) scale(0.6) rotate(-5deg);
		}
		75% {
			opacity: 1;
			transform: translateY(0) scale(1.08);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
	@keyframes name-reveal {
		from {
			opacity: 0;
			transform: translateY(0.5rem);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
	.reduced-motion .voter,
	.reduced-motion .artist-heading,
	.reduced-motion .bonus {
		animation: none;
	}
	@media (prefers-reduced-motion: reduce) {
		.voter,
		.artist-heading,
		.bonus {
			animation: none;
		}
	}
</style>
