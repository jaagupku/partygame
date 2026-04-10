<script lang="ts">
	import 'iconify-icon';

	type ScoreboardPlayer = {
		id: string;
		name: string;
		score: number;
		status: 'connected' | 'disconnected';
		isHost?: boolean;
	};

	interface ScoreboardProps {
		players: ScoreboardPlayer[];
		playerMap: Map<string, ScoreboardPlayer>;
		onSelectPlayer?: (playerId: string) => void;
	}

	let { players, playerMap, onSelectPlayer }: ScoreboardProps = $props();

	const ordered = $derived(
		players
			.filter((player) => !player.isHost)
			.toSorted((a, b) => b.score - a.score)
			.map((player) => player.id)
	);
</script>

<section class="card">
	<h2 class="label-title mb-4 text-3xl">Scoreboard</h2>
	{#if onSelectPlayer}
		<p class="mb-4 text-sm text-slate-600">Click a player name to make them the host controller.</p>
	{/if}
	<ol class="stack-md">
		{#each ordered as playerId, i (i)}
			<li class="grid grid-cols-[auto_1fr_auto] items-center gap-2 rounded-xl bg-white/70 p-3">
				<div class="badge bg-slate-100 text-slate-700">#{i + 1}</div>
				{#if onSelectPlayer}
					<button
						type="button"
						class="flex items-center gap-2 text-left text-lg font-bold text-slate-800 transition-opacity hover:opacity-75"
						onclick={() => onSelectPlayer(playerId)}
					>
						{#if playerMap.get(playerId)?.status === 'disconnected'}
							<iconify-icon icon="fluent:plug-disconnected-16-filled"></iconify-icon>
						{/if}
						{playerMap.get(playerId)?.name}
					</button>
				{:else}
					<div class="flex items-center gap-2 text-lg font-bold">
						{#if playerMap.get(playerId)?.status === 'disconnected'}
							<iconify-icon icon="fluent:plug-disconnected-16-filled"></iconify-icon>
						{/if}
						{playerMap.get(playerId)?.name}
					</div>
				{/if}
				<div class="text-2xl font-extrabold text-sky-700">{playerMap.get(playerId)?.score}</div>
			</li>
		{/each}
	</ol>
</section>
