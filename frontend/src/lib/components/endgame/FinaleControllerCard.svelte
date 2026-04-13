<script lang="ts">
	interface FinaleControllerCardProps {
		endGame: EndGameState;
		playerId: string;
	}

	let { endGame, playerId }: FinaleControllerCardProps = $props();

	const result = $derived(endGame.final_standings.find((entry) => entry.player_id === playerId));
	const placeLabel = $derived.by(() => {
		if (!result) {
			return 'Finished';
		}
		const suffix = getOrdinalSuffix(result.place);
		return `${result.place}${suffix} place`;
	});
	const headline = $derived.by(() => {
		if (!result) {
			return 'Game Complete';
		}
		if (result.place === 1) {
			return 'You won the game';
		}
		if (result.place <= 3) {
			return 'Top 3 finish';
		}
		return 'Final standings are in';
	});

	function getOrdinalSuffix(value: number) {
		const modHundred = value % 100;
		if (modHundred >= 11 && modHundred <= 13) {
			return 'th';
		}
		switch (value % 10) {
			case 1:
				return 'st';
			case 2:
				return 'nd';
			case 3:
				return 'rd';
			default:
				return 'th';
		}
	}
</script>

<section class="card stack-md text-center">
	<p class="text-sm font-black uppercase tracking-[0.18em] text-sky-700">Final Result</p>
	<h2 class="label-title text-3xl">{headline}</h2>
	<p class="text-lg text-slate-600">{placeLabel}</p>
	{#if result}
		<div class="rounded-3xl bg-slate-950 px-5 py-6 text-white">
			<p class="text-sm font-black uppercase tracking-[0.18em] text-sky-200">Score</p>
			<p class="mt-3 text-5xl font-black leading-none">{result.score}</p>
			<p class="mt-2 text-sky-100">points</p>
		</div>
	{:else}
		<p class="text-slate-500">
			Your controller is connected, but you were not included in the final standings.
		</p>
	{/if}
</section>
