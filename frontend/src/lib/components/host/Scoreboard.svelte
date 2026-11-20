<script lang="ts">
	import 'iconify-icon';
	import Avatar from '#lib/components/Avatar.svelte';
	import { messages } from '#lib/i18n.js';

	type ScoreboardPlayer = {
		id: string;
		name: string;
		score: number;
		status: 'connected' | 'disconnected';
		avatar_kind?: 'preset' | 'custom';
		avatar_preset_key?: string;
		avatar_url?: string;
		isHost?: boolean;
	};

	interface ScoreboardProps {
		players: ScoreboardPlayer[];
		playerMap: Map<string, ScoreboardPlayer>;
		onSelectPlayer?: (playerId: string) => void;
		variant?: 'default' | 'rail' | 'overlay';
		standings?: FinalStandingEntry[];
	}

	let {
		players,
		playerMap,
		onSelectPlayer,
		variant = 'default',
		standings
	}: ScoreboardProps = $props();

	const ordered = $derived(
		standings?.length
			? standings.map((entry) => entry.player_id)
			: players
					.filter((player) => !player.isHost)
					.toSorted((a, b) => b.score - a.score)
					.map((player) => player.id)
	);
	const railVariant = $derived(variant === 'rail');
	const overlayVariant = $derived(variant === 'overlay');
	const placeByPlayerId = $derived(
		new Map((standings ?? []).map((entry) => [entry.player_id, entry.place]))
	);
</script>

<section
	class={`scoreboard-card card ${railVariant ? 'xl:sticky xl:top-6' : ''} ${
		overlayVariant ? 'flex h-full min-h-0 flex-col overflow-hidden' : ''
	}`}
>
	<h2
		class={`scoreboard-title label-title mb-4 ${railVariant ? 'text-2xl md:text-3xl' : 'text-3xl'}`}
	>
		{$messages.finale.fullScoreboard}
	</h2>
	{#if onSelectPlayer}
		<p class="theme-text-muted mb-4 text-sm">
			Click a player name to make them the host controller.
		</p>
	{/if}
	<ol class={`stack-md ${overlayVariant ? 'min-h-0 flex-1 overflow-y-auto pr-1' : ''}`}>
		{#each ordered as playerId, i (i)}
			<li
				class={`scoreboard-row theme-surface-muted grid items-center gap-2 rounded-xl border ${
					railVariant
						? 'grid-cols-[auto_minmax(0,1fr)_auto] p-3.5'
						: 'grid-cols-[auto_1fr_auto] p-3'
				}`}
			>
				<div class="scoreboard-place theme-surface badge border">
					#{placeByPlayerId.get(playerId) ?? i + 1}
				</div>
				{#if onSelectPlayer}
					<button
						type="button"
						class={`theme-text flex min-w-0 items-center gap-3 text-left font-bold transition-opacity hover:opacity-75 ${
							railVariant ? 'text-base md:text-lg' : 'text-lg'
						}`}
						onclick={() => onSelectPlayer(playerId)}
					>
						<Avatar
							name={playerMap.get(playerId)?.name ?? playerId}
							avatarKind={playerMap.get(playerId)?.avatar_kind}
							avatarPresetKey={playerMap.get(playerId)?.avatar_preset_key}
							avatarUrl={playerMap.get(playerId)?.avatar_url}
							sizeClass={railVariant ? 'h-10 w-10' : 'h-11 w-11'}
						/>
						{#if playerMap.get(playerId)?.status === 'disconnected'}
							<iconify-icon icon="fluent:plug-disconnected-16-filled"></iconify-icon>
						{/if}
						<span class="truncate">{playerMap.get(playerId)?.name}</span>
					</button>
				{:else}
					<div
						class={`scoreboard-name flex min-w-0 items-center gap-3 font-bold ${
							railVariant ? 'text-base md:text-lg' : 'text-lg'
						}`}
					>
						<Avatar
							name={playerMap.get(playerId)?.name ?? playerId}
							avatarKind={playerMap.get(playerId)?.avatar_kind}
							avatarPresetKey={playerMap.get(playerId)?.avatar_preset_key}
							avatarUrl={playerMap.get(playerId)?.avatar_url}
							sizeClass={railVariant ? 'h-10 w-10' : 'h-11 w-11'}
						/>
						{#if playerMap.get(playerId)?.status === 'disconnected'}
							<iconify-icon icon="fluent:plug-disconnected-16-filled"></iconify-icon>
						{/if}
						<span class="truncate">{playerMap.get(playerId)?.name}</span>
					</div>
				{/if}
				<div
					class={`scoreboard-score font-extrabold ${railVariant ? 'text-xl md:text-2xl' : 'text-2xl'}`}
					style="color: var(--party-primary)"
				>
					{playerMap.get(playerId)?.score}<span class="price-score-unit">
						{$messages.common.pointsWord}</span
					>
				</div>
			</li>
		{/each}
	</ol>
</section>

<style>
	.price-score-unit {
		display: none;
	}
	/* The TV stage: standings read from across the room. */
	:global(.game-stage) .scoreboard-title {
		font-size: var(--tv-subtitle);
	}
	:global(.game-stage) .scoreboard-row {
		gap: 1rem;
		padding: 0.75rem 1.25rem;
	}
	:global(.game-stage) .scoreboard-place {
		font-size: var(--tv-caption);
	}
	:global(.game-stage) .scoreboard-name {
		gap: 1rem;
		font-size: var(--tv-body);
	}
	:global(.game-stage) .scoreboard-name :global(.avatar-shell) {
		width: 3.5rem;
		height: 3.5rem;
	}
	:global(.game-stage) .scoreboard-score {
		font-size: var(--tv-subtitle);
	}
	:global(.game-stage) .scoreboard-score .price-score-unit {
		font-size: var(--tv-caption);
	}
	/* A crowd keeps every row on screen. */
	:global(.game-stage) ol:has(> .scoreboard-row:nth-child(9)) {
		gap: 0.4rem;
	}
	:global(.game-stage) ol:has(> .scoreboard-row:nth-child(9)) > .scoreboard-row {
		padding-block: 0.3rem;
	}
</style>
