<script lang="ts">
	import { locale, messages } from '$lib/i18n';
	import { priceResultDelay, rankPriceResults } from './price-reveal';
	let { step }: { step: RuntimeStepState } = $props();
	const results = $derived(rankPriceResults(step));
	const euro = (minor: number) =>
		new Intl.NumberFormat($locale, { style: 'currency', currency: 'EUR' }).format(minor / 100);
	function answer(value: unknown) {
		if (value === null || value === undefined) return $messages.priceGame.noAnswer;
		return step.price_mode === 'guess'
			? euro(Number(value) * 100)
			: (step.price_products?.find((p) => p.id === value)?.title ?? $messages.priceGame.noAnswer);
	}
</script>

{#if step.price_reveal?.length}
	{#key step.id}
		<section class="price-receipt stack-md mt-4" aria-label={$messages.priceGame.correctPrice}>
			<div class="price-reveal-prices" class:comparison={step.price_reveal.length > 1}>
				{#each step.price_reveal as item}
					<div class="price-checkout-label">
						{#if step.price_reveal.length > 1}
							<p class="price-reveal-product">
								{step.price_products?.find((p) => p.id === item.id)?.title}
							</p>
						{/if}
						<p class="store-eyebrow">{$messages.priceGame.correctPrice}</p>
						<p class="price-amount">{euro(item.price_minor)}</p>
					</div>
				{/each}
			</div>
			<h3 class="text-lg font-bold">{$messages.priceGame.results}</h3>
			<ol class="price-result-list">
				{#each results as result, index (result.player_id)}
					<li
						class="price-result"
						style:--reveal-delay={`${priceResultDelay(index, results.length)}ms`}
					>
						<span class="price-result-rank" aria-hidden="true">{index + 1}</span>
						<div class="price-result-player">
							<p class="font-bold">{result.player_name}</p>
							<p class="price-result-answer">{answer(result.answer)}</p>
						</div>
						<strong class="price-result-points"
							>+{result.points} <span>{$messages.common.pointsWord}</span></strong
						>
					</li>
				{/each}
			</ol>
			<details class="price-product-details">
				<summary>{$messages.priceGame.productDetails}</summary>
				<div class="grid gap-3 pt-3 sm:grid-cols-2">
					{#each step.price_reveal as item}
						<div>
							<p class="font-bold">{step.price_products?.find((p) => p.id === item.id)?.title}</p>
							<p>{$messages.priceGame.actualPrice}: {euro(item.price_minor)}</p>
							<p>
								{$messages.priceGame.retailers[
									item.retailer as keyof typeof $messages.priceGame.retailers
								]}
								· {$messages.priceGame.captured}: {new Date(item.captured_at).toLocaleDateString(
									$locale
								)}
							</p>
							<a class="underline" href={item.source_url} target="_blank" rel="noopener noreferrer"
								>{$messages.priceGame.source}</a
							>
						</div>
					{/each}
				</div>
			</details>
		</section>
	{/key}
{/if}

<style>
	.price-reveal-prices {
		display: grid;
		gap: 0.75rem;
	}
	.price-checkout-label {
		padding: 1rem;
		text-align: center;
	}
	.price-reveal-product {
		font-weight: 700;
		overflow-wrap: anywhere;
		margin-bottom: 0.5rem;
	}
	.price-amount {
		font-size: clamp(3.25rem, 7vw, 7rem);
		font-weight: 900;
		line-height: 1.15;
		letter-spacing: -0.06em;
		overflow-wrap: anywhere;
	}
	.price-result-list {
		display: grid;
		gap: 0;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.price-result {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.65rem 0;
		animation: price-answer-in 220ms ease-out var(--reveal-delay) both;
	}
	.price-result-rank {
		flex: 0 0 1.5rem;
		opacity: 0.6;
		font-variant-numeric: tabular-nums;
	}
	.price-result-player {
		flex: 1;
		min-width: 0;
		overflow-wrap: anywhere;
	}
	.price-result-answer {
		font-variant-numeric: tabular-nums;
	}
	.price-result-points {
		flex-shrink: 0;
		font-size: 1.15rem;
	}
	.price-result-points span {
		font-size: 0.7em;
	}
	.price-product-details {
		font-size: 0.8rem;
	}
	.price-product-details summary {
		cursor: pointer;
		width: fit-content;
	}
	@media (min-width: 640px) {
		.comparison {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.price-result-player {
			display: grid;
			grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
			align-items: center;
			gap: 1rem;
		}
	}
	@keyframes price-answer-in {
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
		.price-result {
			animation: none;
		}
	}
</style>
