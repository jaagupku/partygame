<script lang="ts">
	import Avatar from '$lib/components/Avatar.svelte';
	import GameConnectionStatus from '$lib/components/GameConnectionStatus.svelte';
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
	const formatStatValue = (card: EndGameStatCard) => {
		if (card.unit === 'seconds') {
			return `${Number(card.value).toFixed(2)}s`;
		}
		if (card.unit === 'percent') {
			return `${Number(card.value).toFixed(0)}%`;
		}
		return `${card.value}${card.unit ? ` ${card.unit}` : ''}`;
	};
	const confettiPieces = Array.from({ length: 18 }, (_, index) => index);
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
			<div class="confetti" aria-hidden="true">
				{#each confettiPieces as piece (piece)}
					<span style={`--piece:${piece};`}></span>
				{/each}
			</div>
			<div class="podium-stack">
				{#if visiblePodiumGroups.length === 0}
					<p class="text-lg text-slate-600">{$messages.finale.noFinalStandingsYet}</p>
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
					<p class="stat-label">{card.label}</p>
					<h2 class="stat-winners">{statWinnerNames(card)}</h2>
					<p class="stat-value">{formatStatValue(card)}</p>
					{#if card.description}
						<p class="stat-description">{card.description}</p>
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
			radial-gradient(circle at top, rgb(255 255 255 / 0.95), rgb(255 255 255 / 0.72)),
			linear-gradient(145deg, #fef3c7, #dbeafe 52%, #dcfce7);
	}

	.confetti span {
		position: absolute;
		top: -10%;
		left: calc((var(--piece) + 1) * 5%);
		width: 0.9rem;
		height: 1.6rem;
		border-radius: 999px;
		opacity: 0.9;
		background: hsl(calc(var(--piece) * 22deg) 85% 62%);
		animation: fall 3.6s linear infinite;
		animation-delay: calc(var(--piece) * -0.18s);
		transform: rotate(calc(var(--piece) * 12deg));
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
		background: rgb(255 255 255 / 0.88);
		box-shadow: 0 22px 45px rgb(15 23 42 / 0.14);
		border: 1px solid rgb(255 255 255 / 0.8);
		text-align: center;
		animation: lift-in 500ms ease-out both;
	}

	.place-1 {
		background: linear-gradient(180deg, #fff7cc, #fff);
		box-shadow: 0 24px 50px rgb(202 138 4 / 0.2);
	}

	.place-2 {
		background: linear-gradient(180deg, #eff6ff, #fff);
		box-shadow: 0 22px 45px rgb(37 99 235 / 0.12);
	}

	.place-3 {
		background: linear-gradient(180deg, #fef2f2, #fff);
		box-shadow: 0 22px 45px rgb(190 24 93 / 0.12);
	}

	.podium-place,
	.stat-label {
		font-size: 0.8rem;
		font-weight: 900;
		letter-spacing: 0.18em;
		text-transform: uppercase;
		color: #9a3412;
	}

	.podium-name,
	.stat-winners {
		margin-top: 0.9rem;
		font-size: clamp(1.8rem, 4vw, 3rem);
		font-weight: 900;
		line-height: 1;
		color: #0f172a;
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
		color: #475569;
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
			linear-gradient(135deg, rgb(254 242 242 / 0.9), rgb(255 255 255 / 0.96)),
			linear-gradient(180deg, #fff, #fff);
	}

	.stat-value {
		margin-top: auto;
		padding-top: 1.25rem;
		font-size: clamp(2rem, 5vw, 3.25rem);
		font-weight: 900;
		line-height: 1;
		color: #0369a1;
	}

	.empty-card {
		display: grid;
		place-items: center;
		text-align: center;
	}

	@keyframes fall {
		0% {
			transform: translate3d(0, 0, 0) rotate(0deg);
		}
		100% {
			transform: translate3d(calc((var(--piece) - 8) * 0.6rem), 115vh, 0) rotate(220deg);
		}
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
</style>
