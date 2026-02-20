<script lang="ts">
	import 'iconify-icon';

	interface ScoreboardProps {
		players: Player[];
		playerMap: Map<string, Player>;
	}

	let { players, playerMap }: ScoreboardProps = $props();

	const ordered = $derived(
		players
			.filter((player) => !player.isHost)
			.toSorted((a, b) => b.score - a.score)
			.map((player) => player.id)
	);
</script>

<section class="card">
	<h2 class="label-title mb-4 text-3xl">Scoreboard</h2>
	<ol class="stack-md">
		{#each ordered as playerId, i (i)}
			<li class="grid grid-cols-[auto_1fr_auto] items-center gap-2 rounded-xl bg-white/70 p-3">
				<div class="badge bg-slate-100 text-slate-700">#{i + 1}</div>
				<div class="flex items-center gap-2 text-lg font-bold">
					{#if playerMap.get(playerId)?.status === 'disconnected'}
						<iconify-icon icon="fluent:plug-disconnected-16-filled"></iconify-icon>
					{/if}
					{playerMap.get(playerId)?.name}
				</div>
				<div class="text-2xl font-extrabold text-sky-700">{playerMap.get(playerId)?.score}</div>
			</li>
		{/each}
	</ol>
</section>
