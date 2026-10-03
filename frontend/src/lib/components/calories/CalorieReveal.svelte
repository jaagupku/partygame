<script lang="ts">
	import { messages, locale } from '$lib/i18n';
	import CalorieAttribution from './CalorieAttribution.svelte';
	let { step }: { step: RuntimeStepState } = $props();
	function answer(value: unknown) {
		if (value === null || value === undefined) return $messages.priceGame.noAnswer;
		return step.calorie_mode === 'guess'
			? `${value} ${$messages.calorieGame[step.calorie_products?.[0]?.basis === '100ml' ? 'per100ml' : 'per100g']}`
			: (step.calorie_products?.find((p) => p.id === value)?.title ?? $messages.priceGame.noAnswer);
	}
</script>

{#if step.calorie_reveal?.length}
	<section class="stack-md mt-4" aria-label={$messages.calorieGame.actualPrice}>
		<div class="grid gap-3 sm:grid-cols-2">
			{#each step.calorie_reveal as item}
				<div class="theme-soft-primary rounded-xl border p-3">
					<p class="font-bold">{step.calorie_products?.find((p) => p.id === item.id)?.title}</p>
					<p class="my-2 text-3xl font-extrabold">
						{item.kcal}
						{$messages.calorieGame[item.basis === '100ml' ? 'per100ml' : 'per100g']}
					</p>
					<p class="text-sm">
						{$messages.calorieGame.captured}: {new Date(item.captured_at).toLocaleDateString(
							$locale
						)}
					</p>
					<a class="underline" href={item.source_url} target="_blank" rel="noopener noreferrer"
						>{$messages.priceGame.source}</a
					>
				</div>
			{/each}
		</div>
		<h3 class="text-xl font-bold">{$messages.priceGame.results}</h3>
		<ul class="stack-md">
			{#each step.calorie_results ?? [] as result (result.player_id)}
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
		<CalorieAttribution />
	</section>
{/if}
