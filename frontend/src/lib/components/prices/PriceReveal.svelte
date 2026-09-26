<script lang="ts">
	import { locale, messages } from '$lib/i18n';
	let { step }: { step: RuntimeStepState } = $props();
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
	<section class="stack-md mt-4" aria-label={$messages.priceGame.actualPrice}>
		<div class="grid gap-3 sm:grid-cols-2">
			{#each step.price_reveal as item}
				<div class="theme-soft-primary rounded-xl border p-3">
					<p class="font-bold">{step.price_products?.find((p) => p.id === item.id)?.title}</p>
					<p class="my-2 text-3xl font-extrabold">{euro(item.price_minor)}</p>
					<p class="text-sm">
						{$messages.priceGame.retailers[item.retailer as 'rimi' | 'klick']} · {$messages
							.priceGame.captured}: {new Date(item.captured_at).toLocaleDateString($locale)}
					</p>
					<a class="underline" href={item.source_url} target="_blank" rel="noopener noreferrer"
						>{$messages.priceGame.source}</a
					>
				</div>
			{/each}
		</div>
		<h3 class="text-xl font-bold">{$messages.priceGame.results}</h3>
		<ul class="stack-md">
			{#each step.price_results ?? [] as result (result.player_id)}
				<li
					class="theme-surface flex flex-wrap items-center justify-between gap-2 rounded-xl border p-3"
				>
					<div class="min-w-0">
						<p class="font-bold">{result.player_name}</p>
						<p class="break-words">{answer(result.answer)}</p>
					</div>
					<strong>+{result.points} {$messages.common.pointsWord}</strong>
				</li>
			{/each}
		</ul>
	</section>
{/if}
