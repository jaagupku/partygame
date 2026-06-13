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
	const reactionStatKey = (card: EndGameStatCard) =>
		card.id === 'most_reactions' || card.id === 'signature_reaction' || card.id === 'game_mood'
			? card.id
			: undefined;
	const statLabel = (card: EndGameStatCard) => {
		const key = reactionStatKey(card);
		return key ? $messages.finale.statLabels[key] : card.label;
	};
	const statHeadline = (card: EndGameStatCard) => {
		if (card.headline) {
			return card.headline;
		}
		if (card.id === 'signature_reaction' && card.reaction_key) {
			return $messages.finale.reactionSignatureHeadlines[card.reaction_key](statWinnerNames(card));
		}
		if (card.id === 'game_mood' && card.reaction_key) {
			return $messages.finale.reactionMoodHeadlines[card.reaction_key];
		}
		return statWinnerNames(card);
	};
	const statDescription = (card: EndGameStatCard) => {
		const key = reactionStatKey(card);
		return key ? $messages.finale.statDescriptions[key] : card.description;
	};
	const formatStatValue = (card: EndGameStatCard) => {
		if (card.unit === 'seconds') {
			return `${Number(card.value).toFixed(2)}s`;
		}
		if (card.unit === 'percent') {
			return `${Number(card.value).toFixed(0)}%`;
		}
		if (card.unit === 'reactions' || card.unit === 'uses') {
			return `${card.value} ${$messages.finale.reactionStatUnits[card.unit]}`;
		}
		return `${card.value}${card.unit ? ` ${card.unit}` : ''}`;
	};
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
		<section class="stats-grid">
			{#each endGame.stats_cards as card (card.id)}
				<article class="card stat-card">
					<p class="stat-label">{statLabel(card)}</p>
					{#if card.emoji}
						<p class="stat-emoji" aria-hidden="true">{card.emoji}</p>
					{/if}
					<h2 class="stat-winners">{statHeadline(card)}</h2>
					<p class="stat-value">{formatStatValue(card)}</p>
					{#if statDescription(card)}
						<p class="stat-description">{statDescription(card)}</p>
					{/if}
				</article>
			{/each}
			{#if endGame.stats_cards.length === 0}
				<div class="card stat-card empty-card">
					<p class="stat-label">{$messages.finale.noStatsYet}</p>
					<p class="stat-description">{$messages.finale.noStatsHelp}</p>
				</div>
			{/if}
		</section>
	{:else}
		<section class="h-full min-h-0">
			<Scoreboard {players} {playerMap} variant="overlay" {standings} />
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
		grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
		gap: 1rem;
		align-content: start;
	}

	.stat-card {
		min-height: 14rem;
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
		margin-top: auto;
		padding-top: 1.25rem;
		font-size: clamp(2rem, 5vw, 3.25rem);
		font-weight: 900;
		line-height: 1;
		color: color-mix(in srgb, var(--party-primary-strong), var(--party-ink) 18%);
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
		.podium-card {
			animation: none;
		}
	}
</style>
