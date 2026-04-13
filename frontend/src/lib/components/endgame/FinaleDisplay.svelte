<script lang="ts">
	import Avatar from '$lib/components/Avatar.svelte';
	import GameConnectionStatus from '$lib/components/GameConnectionStatus.svelte';
	import Scoreboard from '$lib/components/host/Scoreboard.svelte';

	interface FinaleDisplayProps {
		endGame: EndGameState;
		players: Player[];
		playerMap: Map<string, Player>;
		title?: string;
		connectionLabel?: string;
		showDisconnectedChip?: boolean;
	}

	let {
		endGame,
		players,
		playerMap,
		title = 'Final Results',
		connectionLabel = 'Live',
		showDisconnectedChip = true
	}: FinaleDisplayProps = $props();

	const stage = $derived(endGame.sequence_stage || 'podium');
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
	const standings = $derived(endGame.final_standings);
</script>

<div class="finale-shell">
	<header class="finale-header">
		<div>
			<h1 class="page-title text-left text-4xl md:text-5xl">{title}</h1>
			<p class="page-subtitle text-left text-base md:text-lg">
				{stage === 'podium'
					? 'Top players revealed'
					: stage === 'stats'
						? 'Best moments from the match'
						: 'Full final scoreboard'}
			</p>
		</div>
		<GameConnectionStatus {connectionLabel} showInline={false} {showDisconnectedChip} />
	</header>

	{#if stage === 'podium'}
		<section class="podium card">
			<div class="confetti" aria-hidden="true">
				{#each confettiPieces as piece (piece)}
					<span style={`--piece:${piece};`}></span>
				{/each}
			</div>
			<div class="podium-grid">
				{#if podiumEntries.length === 0}
					<p class="text-lg text-slate-600">No final standings yet.</p>
				{:else}
					{#each podiumEntries as entry (entry.player_id)}
						<article class={`podium-card place-${Math.min(entry.place, 3)}`}>
							<p class="podium-place">Place #{entry.place}</p>
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
							<p class="podium-score">{entry.score} pts</p>
						</article>
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
					<p class="stat-label">No Stats Yet</p>
					<p class="stat-description">
						This game did not produce enough data for finale highlights.
					</p>
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

	.podium-grid {
		position: relative;
		z-index: 1;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
		gap: 1rem;
		width: min(100%, 60rem);
		align-items: end;
	}

	.podium-card {
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
		transform: translateY(-0.75rem);
	}

	.place-2 {
		background: linear-gradient(180deg, #eff6ff, #fff);
	}

	.place-3 {
		background: linear-gradient(180deg, #fef2f2, #fff);
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
