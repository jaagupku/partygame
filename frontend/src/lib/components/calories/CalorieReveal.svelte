<script lang="ts">
	import { untrack } from 'svelte';
	import ChoiceReveal from '../guessing/ChoiceReveal.svelte';
	import GuessReveal from '../guessing/GuessReveal.svelte';
	import { choiceRevealMs, choiceWinner, rankGuessResults } from '../guessing/guess-reveal';
	import Coach from '$lib/presentation/calorie/Coach.svelte';
	import { calorieReaction } from '$lib/presentation/calorie/reaction';
	import { messages, locale } from '$lib/i18n';
	import CalorieAttribution from './CalorieAttribution.svelte';
	let {
		step,
		playerId,
		showCoach = true,
		players = [],
		choice = false,
		animate = false
	}: {
		step: RuntimeStepState;
		playerId?: string;
		showCoach?: boolean;
		players?: Player[];
		choice?: boolean;
		animate?: boolean;
	} = $props();
	const compare = $derived(step.calorie_mode === 'compare');
	const winner = $derived(
		compare
			? choiceWinner((step.calorie_reveal ?? []).map((item) => ({ id: item.id, value: item.kcal })))
			: undefined
	);
	const values = $derived(
		(step.calorie_reveal ?? []).map((item) => ({
			id: item.id,
			title: step.calorie_products?.find((p) => p.id === item.id)?.title,
			value: new Intl.NumberFormat($locale).format(item.kcal),
			unit: $messages.calorieGame[item.basis === '100ml' ? 'per100ml' : 'per100g'],
			correct: item.id === winner,
			...(compare ? {} : { amount: item.kcal, format: new Intl.NumberFormat($locale).format })
		}))
	);
	const choiceMs = $derived(
		choiceRevealMs(
			step.calorie_results ?? [],
			(step.calorie_products ?? []).map((p) => p.id)
		)
	);
	let coachReady = $state(true);
	/** Runs when the reveal section mounts: an animated choice reveal holds the coach's reaction. */
	function holdCoach(_node: HTMLElement) {
		if (!untrack(() => choice && compare && animate)) return;
		coachReady = false;
		const timer = setTimeout(
			() => (coachReady = true),
			untrack(() => choiceMs)
		);
		return { destroy: () => clearTimeout(timer) };
	}
	const reaction = $derived(calorieReaction(step.calorie_results, playerId));
	const results = $derived(
		rankGuessResults(step.calorie_results ?? [], step.calorie_mode === 'guess', (answer) => {
			const kcal = step.calorie_reveal?.[0]?.kcal;
			const value = Number(answer);
			return kcal !== undefined && Number.isFinite(value) ? Math.abs(value - kcal) : Infinity;
		})
	);
	function answer(value: unknown) {
		if (value === null || value === undefined) return $messages.priceGame.noAnswer;
		return step.calorie_mode === 'guess'
			? `${value} ${$messages.calorieGame[step.calorie_products?.[0]?.basis === '100ml' ? 'per100ml' : 'per100g']}`
			: (step.calorie_products?.find((p) => p.id === value)?.title ?? $messages.priceGame.noAnswer);
	}
</script>

{#if step.calorie_reveal?.length}
	{#key step.id}
		<!-- The coach reacts after the products and avatars. -->
		{#if choice && compare}<ChoiceReveal
				products={step.calorie_products ?? []}
				{values}
				correctId={winner}
				results={step.calorie_results ?? []}
				{players}
				winnerLabel={$messages.calorieGame.moreCalories}
				{animate}
			/>{/if}
		<section
			class="calorie-reveal stack-md mt-4"
			aria-label={$messages.calorieGame.actualPrice}
			use:holdCoach
		>
			{#if showCoach}<Coach
					pose={!coachReady ? 'thinking' : reaction === 'close' ? 'celebrate' : 'reveal'}
					message={coachReady ? $messages.calorieStudio[reaction] : ''}
				/>{:else}<p class="font-bold">{$messages.calorieStudio[reaction]}</p>{/if}
			<GuessReveal
				values={choice && compare ? [] : values}
				label={$messages.calorieGame.correctCalories}
				winnerLabel={$messages.calorieGame.moreCalories}
				delayOffset={choice && compare && animate ? choiceMs : 0}
				{results}
				{answer}
				{animate}
			/>
			<ul class="calorie-product-details">
				{#each step.calorie_reveal as item}
					<li>
						{#if step.calorie_reveal.length > 1}<strong
								>{step.calorie_products?.find((p) => p.id === item.id)?.title}</strong
							>{' · '}{/if}{$messages.calorieGame.captured}: {new Date(
							item.captured_at
						).toLocaleDateString($locale)}
						·
						<a class="underline" href={item.source_url} target="_blank" rel="noopener noreferrer"
							>{$messages.priceGame.source}</a
						>
					</li>
				{/each}
			</ul>
			<CalorieAttribution />
		</section>
	{/key}
{/if}

<style>
	/* Capture dates and sources remain visible on the reveal. */
	.calorie-product-details {
		display: grid;
		gap: 0.25rem;
		margin: 0;
		padding: 0;
		list-style: none;
		font-size: 0.8rem;
		overflow-wrap: anywhere;
	}
</style>
