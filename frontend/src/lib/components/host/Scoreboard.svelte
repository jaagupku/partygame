<script lang="ts">
	export let players: Player[];
	export let playerMap: Map<string, Player>;

	$: ordered = players
		.toSorted((a, b) => a.score - b.score)
		.filter((player) => !player.isHost)
		.map((player) => player.id);
</script>

<h1 class="h1">Scoreboard:</h1>
<ol class="list">
	{#each ordered as playerId, i (i)}
		<li>
			<div class="w-full grid grid-cols-[auto_1fr_auto]">
				<div class="bg-surface-500/30 p-4 rounded-l-xl">{i + 1}</div>
				<div class="bg-surface-500/30 p-4">
					{#if playerMap.get(playerId)?.status === 'disconnected'}
						<iconify-icon icon="fluent:plug-disconnected-16-filled" />
					{/if}
					{playerMap.get(playerId)?.name}
				</div>
				<div class="bg-surface-500/30 p-4 rounded-r-xl">{playerMap.get(playerId)?.score}</div>
			</div>
		</li>
	{/each}
</ol>
