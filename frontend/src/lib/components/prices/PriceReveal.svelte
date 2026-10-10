<script lang="ts">
	import { locale, messages } from '$lib/i18n';
	import ChoiceReveal from '../guessing/ChoiceReveal.svelte';
	import GuessReveal from '../guessing/GuessReveal.svelte';
	import { choiceRevealMs, choiceWinner } from '../guessing/guess-reveal';
	import { rankPriceResults } from './price-reveal';
	let {
		step,
		players = [],
		choice = false,
		animate = false
	}: { step: RuntimeStepState; players?: Player[]; choice?: boolean; animate?: boolean } = $props();
	const results = $derived(rankPriceResults(step));
	const compare = $derived(step.price_mode === 'compare');
	const winner = $derived(
		compare
			? choiceWinner(
					(step.price_reveal ?? []).map((item) => ({ id: item.id, value: item.price_minor }))
				)
			: undefined
	);
	const values = $derived(
		(step.price_reveal ?? []).map((item) => ({
			id: item.id,
			title: step.price_products?.find((p) => p.id === item.id)?.title,
			value: euro(item.price_minor),
			correct: item.id === winner,
			...(compare ? {} : { amount: item.price_minor, format: euro })
		}))
	);
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
		<!-- Products and avatars stay on the shop floor; the receipt follows. -->
		{#if choice && compare}<ChoiceReveal
				products={step.price_products ?? []}
				{values}
				correctId={winner}
				results={step.price_results ?? []}
				{players}
				winnerLabel={$messages.priceGame.moreExpensive}
				{animate}
			/>{/if}
		<section class="price-receipt stack-md mt-4" aria-label={$messages.priceGame.correctPrice}>
			<GuessReveal
				values={choice && compare ? [] : values}
				label={$messages.priceGame.correctPrice}
				winnerLabel={$messages.priceGame.moreExpensive}
				delayOffset={choice && compare && animate
					? choiceRevealMs(
							step.price_results ?? [],
							(step.price_products ?? []).map((p) => p.id)
						)
					: 0}
				{results}
				{answer}
				{animate}
			/>
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
	.price-product-details {
		font-size: 0.8rem;
	}
	.price-product-details summary {
		cursor: pointer;
		width: fit-content;
	}
</style>
