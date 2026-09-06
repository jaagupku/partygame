<script lang="ts">
	import Avatar from '$lib/components/Avatar.svelte';
	import GameConnectionStatus from '$lib/components/GameConnectionStatus.svelte';
	import CelebrationBackground from '$lib/components/endgame/CelebrationBackground.svelte';
	import Scoreboard from '$lib/components/host/Scoreboard.svelte';
	import { messages } from '$lib/i18n';

	interface FinaleDisplayProps {
		endGame: EndGameState;
		players: Player[];
		playerMap: Map<string, Player>;
		title?: string;
		connectionLabel?: string;
		connected?: boolean | null;
		showDisconnectedChip?: boolean;
	}

	let {
		endGame,
		players,
		playerMap,
		title = '',
		connectionLabel = '',
		connected = null,
		showDisconnectedChip = true
	}: FinaleDisplayProps = $props();

	const stage = $derived(endGame.sequence_stage || 'third_place');
	const statWinnerNames = (card: EndGameStatCard) =>
		card.winner_player_ids.map((playerId) => playerMap.get(playerId)?.name ?? playerId).join(', ');
	const highlights = $derived.by(() => {
		const ids = endGame.highlight_card_ids;
		return ids?.length
			? ids
					.map((id) => endGame.stats_cards.find((card) => card.id === id))
					.filter((card): card is EndGameStatCard => Boolean(card))
					.slice(0, 3)
			: endGame.stats_cards.filter((card) => card.id !== 'most_wrong').slice(0, 3);
	});
	const statLabel = (card: EndGameStatCard) =>
		$messages.finale.statLabels[card.id as keyof typeof $messages.finale.statLabels] ?? card.label;
	const statDescription = (card: EndGameStatCard) =>
		$messages.finale.statDescriptions[card.id as keyof typeof $messages.finale.statDescriptions] ??
		card.description;
	const formatStatValue = (card: EndGameStatCard) =>
		card.unit === 'seconds'
			? Number(card.value).toFixed(2)
			: card.unit === 'percent'
				? `${Number(card.value).toFixed(0)}%`
				: `${card.value}`;
	const statUnit = (card: EndGameStatCard) => {
		const unit = card.unit ?? (card.id === 'most_correct' ? 'answers' : '');
		return $messages.finale.statUnits[unit as keyof typeof $messages.finale.statUnits] ?? unit;
	};
	const supportingFacts = (card: EndGameStatCard) =>
		card.winner_player_ids.length === 0
			? []
			: endGame.stats_cards
					.filter(
						(other) =>
							other.id !== card.id &&
							['most_correct', 'fastest_buzz', 'highest_accuracy'].includes(other.id) &&
							other.winner_player_ids.length === card.winner_player_ids.length &&
							other.winner_player_ids.every((id) => card.winner_player_ids.includes(id))
					)
					.slice(0, 2);
	const podiumEntries = $derived(endGame.podium.toSorted((a, b) => a.place - b.place));
	const visiblePodiumPlaces = $derived.by(() => {
		if (stage === 'third_place') {
			return new Set([3]);
		}
		if (stage === 'second_place') {
			return new Set([2, 3]);
		}
		if (stage === 'first_place') {
			return new Set([1, 2, 3]);
		}
		return new Set<number>();
	});
	const visiblePodiumGroups = $derived.by(() => {
		const grouped = new Map<number, FinalStandingEntry[]>();
		for (const entry of podiumEntries) {
			if (!visiblePodiumPlaces.has(entry.place)) {
				continue;
			}
			const bucket = grouped.get(entry.place) ?? [];
			bucket.push(entry);
			grouped.set(entry.place, bucket);
		}
		return [...grouped.entries()]
			.sort(([leftPlace], [rightPlace]) => leftPlace - rightPlace)
			.map(([place, entries]) => ({ place, entries }));
	});
	const standings = $derived(endGame.final_standings);
</script>

<div class="finale-shell">
	<header class="finale-header">
		<div>
			<h1 class="page-title text-left text-4xl md:text-5xl">{title}</h1>
			<p class="page-subtitle text-left text-base md:text-lg">
				{stage === 'third_place'
					? $messages.finale.thirdPlaceReveal
					: stage === 'second_place'
						? $messages.finale.secondPlaceReveal
						: stage === 'first_place'
							? $messages.finale.firstPlaceReveal
							: stage === 'stats'
								? $messages.finale.bestMoments
								: $messages.finale.fullScoreboard}
			</p>
		</div>
		<GameConnectionStatus {connected} {connectionLabel} showInline={false} {showDisconnectedChip} />
	</header>

	{#if stage === 'third_place' || stage === 'second_place' || stage === 'first_place'}
		<section class="podium card">
			<CelebrationBackground {stage} />
			<div class="podium-stack">
				{#if visiblePodiumGroups.length === 0}
					<p class="theme-text-muted text-lg">{$messages.finale.noFinalStandingsYet}</p>
				{:else}
					{#each visiblePodiumGroups as group (group.place)}
						<section class={`podium-row place-${Math.min(group.place, 3)}`}>
							<p class="podium-place">{$messages.finale.place(group.place)}</p>
							<div class="podium-row-cards">
								{#each group.entries as entry (entry.player_id)}
									<article class={`podium-card place-${Math.min(entry.place, 3)}`}>
										<div class="podium-avatar-wrap">
											<Avatar
												name={entry.name}
												avatarKind={entry.avatar_kind}
												avatarPresetKey={entry.avatar_preset_key}
												avatarUrl={entry.avatar_url}
												sizeClass="h-28 w-28 md:h-32 md:w-32"
												className="podium-avatar"
											/>
										</div>
										<h2 class="podium-name">{entry.name}</h2>
										<p class="podium-score">{entry.score} {$messages.common.pointsWord}</p>
									</article>
								{/each}
							</div>
						</section>
					{/each}
				{/if}
			</div>
		</section>
	{:else if stage === 'stats'}
		<section class="stats-grid" style:--card-count={Math.max(1, highlights.length)}>
			{#each highlights as card, index (card.id)}
				<article class="card stat-card" style:--reveal-delay={`${index * 700}ms`}>
					<p class="stat-label">{statLabel(card)}</p>
					<div class="stat-identity">
						<div class="stat-avatars">
							{#each card.winner_player_ids as playerId (playerId)}
								{@const player =
									playerMap.get(playerId) ??
									endGame.final_standings.find((entry) => entry.player_id === playerId)}
								<Avatar
									name={player?.name ?? playerId}
									avatarKind={player?.avatar_kind}
									avatarPresetKey={player?.avatar_preset_key}
									avatarUrl={player?.avatar_url}
									sizeClass="h-16 w-16"
								/>
							{/each}
							{#if card.emoji || card.winner_player_ids.length === 0}
								<span class="stat-emoji" aria-hidden="true">{card.emoji ?? '✨'}</span>
							{/if}
						</div>
						<h2 class="stat-winners">{statWinnerNames(card) || $messages.finale.room}</h2>
						{#if card.winner_player_ids.length > 1}<p class="stat-tie">
								{$messages.finale.tiedAward}
							</p>{/if}
					</div>
					<div class="stat-result">
						<p class="stat-value">{formatStatValue(card)}</p>
						<p class="stat-unit">{statUnit(card)}</p>
					</div>
					<div class="stat-caption">
						{#if card.id === 'highest_accuracy'}
							{#each card.winner_player_ids as playerId}
								{#if card.answer_counts?.[playerId] != null && card.correct_counts?.[playerId] != null}
									<p class="stat-description">
										{card.winner_player_ids.length > 1
											? `${playerMap.get(playerId)?.name ?? playerId}: `
											: ''}{$messages.finale.accuracyDetail(
											card.correct_counts[playerId],
											card.answer_counts[playerId]
										)}
									</p>
								{/if}
							{/each}
						{/if}
						<p class="stat-description">{statDescription(card)}</p>
					</div>
					{#if supportingFacts(card).length}
						<div class="stat-supporting">
							{#each supportingFacts(card) as fact}<p>
									{statLabel(fact)} · {formatStatValue(fact)}
									{statUnit(fact)}
								</p>{/each}
						</div>
					{/if}
				</article>
			{/each}
			{#if highlights.length === 0}
				<div class="card stat-card empty-card">
					<p class="stat-label">{$messages.finale.noStatsYet}</p>
					<p class="stat-description">{$messages.finale.noStatsHelp}</p>
				</div>
			{/if}
		</section>
	{:else}
		<section class="scoreboard-with-recap">
			<div class="min-h-0"><Scoreboard {players} {playerMap} variant="overlay" {standings} /></div>
			{#if highlights.length}
				<aside class="highlights-recap" aria-label={$messages.finale.highlightsRecap}>
					{#each highlights as card (card.id)}
						<p>
							<strong>{statLabel(card)}</strong><span
								>{statWinnerNames(card) || $messages.finale.room} · {formatStatValue(card)}
								{statUnit(card)}</span
							>
						</p>
					{/each}
				</aside>
			{/if}
		</section>
	{/if}
</div>

<style>
	.finale-shell {
		display: grid;
		grid-template-rows: auto minmax(0, 1fr);
		gap: 1rem;
		height: 100%;
		min-height: 0;
	}

	.finale-header {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		align-items: start;
	}

	.podium {
		position: relative;
		display: grid;
		place-items: center;
		min-height: 100%;
		overflow: hidden;
		background:
			radial-gradient(
				circle at 50% 8%,
				color-mix(in srgb, var(--party-surface-strong), transparent 12%),
				transparent 32%
			),
			radial-gradient(
				circle at 18% 24%,
				color-mix(in srgb, var(--party-accent), transparent 64%),
				transparent 34%
			),
			radial-gradient(
				circle at 82% 18%,
				color-mix(in srgb, var(--party-primary), transparent 62%),
				transparent 32%
			),
			linear-gradient(145deg, var(--party-bg-c), var(--party-bg-b) 52%, var(--party-bg-a));
	}

	.podium-stack {
		position: relative;
		z-index: 1;
		display: grid;
		gap: 1rem;
		width: min(100%, 72rem);
		align-content: start;
	}

	.podium-row {
		display: grid;
		gap: 0.75rem;
		justify-items: center;
	}

	.podium-row-cards {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 1rem;
		width: 100%;
	}

	.podium-card {
		width: min(100%, 16rem);
		border-radius: 1.5rem;
		padding: 1.5rem;
		background: color-mix(in srgb, var(--party-surface-strong), transparent 8%);
		box-shadow: 0 22px 45px rgb(15 23 42 / 0.14);
		border: 1px solid var(--party-border);
		color: var(--party-ink);
		text-align: center;
		animation: lift-in 500ms ease-out both;
	}

	.place-1 {
		background: linear-gradient(
			180deg,
			color-mix(in srgb, #fbbf24, var(--party-surface-strong) 62%),
			var(--party-surface-strong)
		);
		box-shadow: 0 24px 50px rgb(202 138 4 / 0.2);
	}

	.place-2 {
		background: linear-gradient(
			180deg,
			color-mix(in srgb, var(--party-primary), var(--party-surface-strong) 78%),
			var(--party-surface-strong)
		);
		box-shadow: 0 22px 45px rgb(37 99 235 / 0.12);
	}

	.place-3 {
		background: linear-gradient(
			180deg,
			color-mix(in srgb, var(--party-accent), var(--party-surface-strong) 78%),
			var(--party-surface-strong)
		);
		box-shadow: 0 22px 45px rgb(190 24 93 / 0.12);
	}

	.podium-place,
	.stat-label {
		font-size: 0.8rem;
		font-weight: 900;
		letter-spacing: 0.18em;
		text-transform: uppercase;
		color: color-mix(in srgb, var(--party-accent-strong), var(--party-ink) 28%);
	}

	.podium-name,
	.stat-winners {
		margin-top: 0.9rem;
		font-size: clamp(1.8rem, 4vw, 3rem);
		font-weight: 900;
		line-height: 1;
		color: var(--party-ink);
	}

	.stat-emoji {
		margin-top: 0.7rem;
		font-size: clamp(3rem, 8vw, 5.5rem);
		line-height: 1;
		filter: drop-shadow(0 14px 20px rgb(15 23 42 / 0.18));
	}

	.podium-avatar-wrap {
		display: grid;
		place-items: center;
		margin-top: 0.9rem;
	}

	.podium-score,
	.stat-description {
		margin-top: 0.75rem;
		font-size: 1rem;
		color: var(--party-subtle);
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(var(--card-count), minmax(0, 1fr));
		width: min(100%, 90rem);
		justify-self: center;
		min-height: 0;
		overflow-y: auto;
		gap: 1rem;
		align-content: start;
	}

	.stat-card {
		display: flex;
		flex-direction: column;
		gap: 1.1rem;
		min-width: 0;
		padding: clamp(1.25rem, 2.5vw, 2.5rem);
		animation: lift-in 450ms ease-out both;
		animation-delay: var(--reveal-delay, 0ms);
		background:
			linear-gradient(
				135deg,
				color-mix(in srgb, var(--party-accent), var(--party-surface-strong) 88%),
				color-mix(in srgb, var(--party-primary), var(--party-surface-strong) 90%)
			),
			var(--party-surface-strong);
		color: var(--party-ink);
	}

	.stat-value {
		margin: 0;
		font-size: clamp(3rem, 6vw, 5.5rem);
		font-weight: 900;
		line-height: 1;
		color: color-mix(in srgb, var(--party-primary), var(--party-ink) 70%);
	}

	.stat-identity {
		min-height: 8rem;
	}
	.stat-avatars {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem;
	}
	.stat-avatars .stat-emoji {
		margin: 0;
		font-size: 3.5rem;
	}
	.stat-winners {
		font-size: clamp(1.5rem, 2.8vw, 2.6rem);
		line-height: 1.1;
		overflow-wrap: anywhere;
	}
	.stat-tie,
	.stat-unit {
		color: var(--party-subtle);
		font-size: 1rem;
	}
	.stat-result {
		margin-top: 0.25rem;
	}
	.stat-description {
		margin-top: 0;
		font-size: 1.05rem;
	}
	.stat-caption {
		display: grid;
		gap: 0.4rem;
	}
	.stat-supporting {
		border-top: 1px solid var(--party-border);
		padding-top: 0.75rem;
		font-size: 0.9rem;
		color: var(--party-subtle);
	}
	.scoreboard-with-recap {
		display: grid;
		grid-template-rows: minmax(0, 1fr) auto;
		min-height: 0;
		gap: 0.75rem;
	}
	.highlights-recap {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem 2rem;
	}
	.highlights-recap p {
		display: grid;
		gap: 0.2rem;
		font-size: 0.9rem;
	}
	.highlights-recap span {
		color: var(--party-subtle);
	}
	@media (max-width: 760px) {
		.stats-grid {
			grid-template-columns: 1fr;
		}
		.stat-identity {
			min-height: 0;
		}
	}
	.empty-card {
		display: grid;
		place-items: center;
		text-align: center;
	}

	@keyframes lift-in {
		from {
			opacity: 0;
			transform: translateY(1rem);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@media (max-width: 640px) {
		.finale-header {
			flex-direction: column;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.podium-card,
		.stat-card {
			animation: none;
		}
	}
</style>
