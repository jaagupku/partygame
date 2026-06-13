<script lang="ts">
	import { messages } from '$lib/i18n';

	interface FinaleControllerCardProps {
		endGame: EndGameState;
		playerId: string;
	}

	let { endGame, playerId }: FinaleControllerCardProps = $props();

	const result = $derived(endGame.final_standings.find((entry) => entry.player_id === playerId));
	const placeLabel = $derived.by(() => {
		if (!result) {
			return $messages.finale.finished;
		}
		return $messages.finale.place(result.place);
	});
	const headline = $derived.by(() => {
		if (!result) {
			return $messages.finale.gameComplete;
		}
		if (result.place === 1) {
			return $messages.finale.youWonTheGame;
		}
		if (result.place <= 3) {
			return $messages.finale.topThreeFinish;
		}
		return $messages.finale.finalStandingsIn;
	});
</script>

<section class="card stack-md text-center">
	<p class="theme-text-muted text-sm font-black uppercase tracking-[0.18em]">
		{$messages.common.finalResult}
	</p>
	<h2 class="label-title text-3xl">{headline}</h2>
	<p class="theme-text-muted text-lg">{placeLabel}</p>
	{#if result}
		<div class="theme-soft-primary rounded-3xl border px-5 py-6">
			<p class="text-sm font-black uppercase tracking-[0.18em]">
				{$messages.common.score}
			</p>
			<p class="mt-3 text-5xl font-black leading-none">{result.score}</p>
			<p class="theme-text-muted mt-2">{$messages.common.pointsWord}</p>
		</div>
	{:else}
		<p class="theme-text-muted">{$messages.finale.notIncludedInStandings}</p>
	{/if}
</section>
