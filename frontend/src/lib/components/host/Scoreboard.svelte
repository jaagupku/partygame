<script lang="ts">
	export let players: Player[];

	$: map = players.reduce(function (map, player) {
		map.set(player.id, player);
		return map;
	}, new Map<string, Player>());

	$: ordered = players.toSorted((a, b) => a.score - b.score).map((player) => player.id);
</script>

<h1 class="h1">Scoreboard:</h1>
<ol class="list">
	{#each ordered as playerId, i (i)}
		<li>
			<div class="w-full grid grid-cols-[auto_1fr_auto]">
				<div class="bg-surface-500/30 p-4 rounded-l-xl">{i + 1}</div>
				<div class="bg-surface-500/30 p-4">
					{#if map.get(playerId)?.status === 'disconnected'}
						<iconify-icon icon="fluent:plug-disconnected-16-filled" />
					{/if}
					{map.get(playerId)?.name}
				</div>
				<div class="bg-surface-500/30 p-4 rounded-r-xl">{map.get(playerId)?.score}</div>
			</div>
		</li>
	{/each}
</ol>
