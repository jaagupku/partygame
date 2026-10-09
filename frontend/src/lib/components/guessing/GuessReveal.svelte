<script lang="ts">
	import { messages } from '$lib/i18n';
	import { resultDelay } from './guess-reveal';
	let {
		values,
		label,
		results,
		answer,
		winnerLabel = '',
		delayOffset = 0
	}: {
		/** Empty when another component already shows the correct values. */
		values: { title?: string; value: string; unit?: string; correct?: boolean }[];
		label: string;
		results: PriceResult[];
		answer: (value: unknown) => string;
		winnerLabel?: string;
		delayOffset?: number;
	} = $props();
	const hasWinner = $derived(values.some((item) => item.correct));
</script>

{#if values.length}<div class="guess-reveal-values" class:comparison={values.length > 1}>
		{#each values as item}
			<div
				class="guess-reveal-value"
				class:guess-reveal-correct={item.correct}
				class:guess-reveal-other={hasWinner && !item.correct}
			>
				{#if item.correct && winnerLabel}<p class="guess-reveal-winner">{winnerLabel}</p>{/if}
				{#if values.length > 1}
					<p class="guess-reveal-title">
						{item.title}
					</p>
				{/if}
				<p class="guess-reveal-label">{label}</p>
				<p class="guess-reveal-amount">
					<strong>{item.value}</strong>{#if item.unit}{' '}<span class="guess-reveal-unit"
							>{item.unit}</span
						>{/if}
				</p>
			</div>
		{/each}
	</div>{/if}
<h3 class="text-lg font-bold">{$messages.priceGame.results}</h3>
<ol class="guess-result-list">
	{#each results as result, index (result.player_id)}
		<li
			class="guess-result"
			style:--reveal-delay={`${delayOffset + resultDelay(index, results.length)}ms`}
		>
			<span class="guess-result-rank" aria-hidden="true">{index + 1}</span>
			<div class="guess-result-player">
				<p class="font-bold">{result.player_name}</p>
				<p class="guess-result-answer">{answer(result.answer)}</p>
			</div>
			<strong class="guess-result-points"
				>+{result.points} <span>{$messages.common.pointsWord}</span></strong
			>
		</li>
	{/each}
</ol>

<style>
	.guess-reveal-values {
		display: grid;
		gap: 0.75rem;
	}
	.guess-reveal-value {
		padding: 1rem;
		text-align: center;
	}
	.guess-reveal-title {
		font-weight: 700;
		overflow-wrap: anywhere;
		margin-bottom: 0.5rem;
	}
	.guess-reveal-amount {
		font-size: clamp(3.25rem, 7vw, 7rem);
		font-weight: 900;
		line-height: 1.15;
		letter-spacing: -0.06em;
		overflow-wrap: anywhere;
	}
	.guess-reveal-other {
		opacity: 0.6;
	}
	.guess-reveal-winner {
		display: inline-block;
		margin-bottom: 0.4rem;
		padding: 0.2rem 0.8rem;
		border-radius: 999px;
		background: var(--party-accent);
		color: var(--party-ink);
		font-size: 0.85rem;
		font-weight: 900;
	}
	.guess-reveal-unit {
		display: block;
		font-size: 1.1rem;
		letter-spacing: normal;
		font-weight: 600;
	}
	.guess-result-list {
		display: grid;
		gap: 0;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.guess-result {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.65rem 0;
		animation: guess-answer-in 220ms ease-out var(--reveal-delay) both;
	}
	.guess-result-rank {
		flex: 0 0 1.5rem;
		opacity: 0.6;
		font-variant-numeric: tabular-nums;
	}
	.guess-result-player {
		flex: 1;
		min-width: 0;
		overflow-wrap: anywhere;
	}
	.guess-result-answer {
		font-variant-numeric: tabular-nums;
	}
	.guess-result-points {
		flex-shrink: 0;
		font-size: 1.15rem;
	}
	.guess-result-points span {
		font-size: 0.7em;
	}
	@media (min-width: 640px) {
		.comparison {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.guess-result-player {
			display: grid;
			grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
			align-items: center;
			gap: 1rem;
		}
	}
	@keyframes guess-answer-in {
		from {
			opacity: 0;
			visibility: hidden;
			transform: translateY(0.35rem);
		}
		to {
			opacity: 1;
			visibility: visible;
			transform: translateY(0);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.guess-result {
			animation: none;
		}
	}
</style>
