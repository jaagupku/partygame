<script lang="ts">
	import Coach from '#lib/presentation/calorie/Coach.svelte';
	import CalorieReveal from '#lib/components/calories/CalorieReveal.svelte';
	import ProductCard from '#lib/components/prices/ProductCard.svelte';
	import PriceReveal from '#lib/components/prices/PriceReveal.svelte';
	import PriceTransition from '#lib/presentation/price/PriceTransition.svelte';
	import { flip } from 'svelte/animate';
	import ImageQuestionMedia from '#lib/components/ImageQuestionMedia.svelte';
	import AudioQuestionMedia from '#lib/components/AudioQuestionMedia.svelte';
	import StepBodyMarkdown from '#lib/components/markdown/StepBodyMarkdown.svelte';
	import VideoQuestionMedia from '#lib/components/VideoQuestionMedia.svelte';
	import { messages } from '#lib/i18n.js';
	import {
		buildOrderingRevealItems,
		buildRevealedOptionStates,
		formatRevealValue,
		isOrderingRevealStep,
		isOptionRevealStep
	} from '#lib/reveal-format.js';

	interface QuestionCardProps {
		step?: RuntimeStepState;
		revealedSubmission?: RevealedSubmission;
		revealedAnswer?: RevealedAnswer;
		buzzerActive?: boolean;
		buzzedPlayerName?: string;
		displayPhase?: string;
		variant?: 'default' | 'stage';
		showCoach?: boolean;
		/** Players for avatars in the animated choice reveal. */
		players?: Player[];
		/** Main display only: compare reveals move avatars to the chosen product. */
		choiceReveal?: boolean;
	}

	let {
		step,
		revealedSubmission,
		revealedAnswer,
		buzzerActive = false,
		buzzedPlayerName,
		displayPhase = 'question_active',
		showCoach = true,
		players = [],
		choiceReveal = false,
		variant = 'default'
	}: QuestionCardProps = $props();

	const productMode = $derived(step?.calorie_mode ?? step?.price_mode);
	const products = $derived(
		step?.calorie_products?.length ? step.calorie_products : (step?.price_products ?? [])
	);
	const productCopy = $derived(
		step?.calorie_mode ? { ...$messages.priceGame, ...$messages.calorieGame } : $messages.priceGame
	);
	const stageVariant = $derived(variant === 'stage');
	const showingAnswerReveal = $derived(displayPhase === 'answer_reveal');
	// Animate only a reveal that follows this card showing the question, never a reconnect or review.
	let questionSeenFor = $state<string>();
	$effect(() => {
		if (step && !showingAnswerReveal) questionSeenFor = step.id;
	});
	const choiceActive = $derived(choiceReveal && productMode === 'compare' && showingAnswerReveal);
	const animateChoice = $derived(questionSeenFor === step?.id);
	const optionRevealStep = $derived(isOptionRevealStep(step));
	const optionStates = $derived.by(() =>
		step && optionRevealStep ? buildRevealedOptionStates(step, revealedAnswer) : []
	);
	const showOptionGrid = $derived(
		Boolean(step?.input_options.length) && optionRevealStep && !productMode
	);
	const orderingRevealStep = $derived(isOrderingRevealStep(step));
	const orderingItems = $derived.by(() =>
		step && orderingRevealStep
			? buildOrderingRevealItems(step, revealedAnswer, showingAnswerReveal)
			: []
	);
	const showOrderingList = $derived(Boolean(step?.input_options.length) && orderingRevealStep);
	const showInlineRevealedAnswer = $derived(
		showingAnswerReveal &&
			!productMode &&
			revealedAnswer &&
			!stageVariant &&
			!optionRevealStep &&
			!orderingRevealStep
	);
	const isBuzzerStep = $derived(step?.input_kind === 'buzzer');
	const shouldPauseMedia = $derived(
		Boolean(step?.media?.paused) || (isBuzzerStep && !buzzerActive)
	);
	const shouldResumePausedMedia = $derived.by(() => {
		const media = step?.media;
		if (!media) {
			return false;
		}
		return !media.paused && (!isBuzzerStep || buzzerActive);
	});
	const fullCreditPointsLabel = $derived(
		step ? `${step.max_points ?? step.evaluation_points} ${$messages.common.pointsWord}` : ''
	);

	function orderingItemKey(items: string[], item: string, index: number) {
		const occurrence = items.slice(0, index + 1).filter((value) => value === item).length;
		return `${item}::${occurrence}`;
	}
</script>

<section
	class={`question-card overflow-hidden ${
		stageVariant ? 'question-card-stage-shell question-card-stage' : 'card stack-md'
	} ${showingAnswerReveal ? 'question-card-reveal-pulse' : ''}`}
	class:question-card-price-stage={stageVariant && Boolean(productMode)}
	class:question-card-price-reveal={stageVariant && Boolean(productMode) && showingAnswerReveal}
>
	{#if step}
		<div class="question-card-title-row">
			<!-- During the reveal, CalorieReveal shows the coach's reaction instead. -->
			{#if step.calorie_mode && showCoach && !showingAnswerReveal && !stageVariant}<Coach
					compact
					pose="thinking"
				/>{/if}
			<h3
				class={`question-card-step-title ${
					stageVariant
						? 'text-[clamp(1.8rem,calc(3.4*var(--stage-vw)),3.6rem)] font-extrabold leading-tight'
						: 'text-3xl font-extrabold'
				}`}
			>
				{productMode ? productCopy[productMode] : step.title}
			</h3>
			<span class={`question-card-points-badge ${stageVariant ? 'points-badge-stage' : ''}`}>
				{fullCreditPointsLabel}
			</span>
		</div>
		{#if productMode}
			<div class:price-stage-content={stageVariant}>
				<div class:price-stage-inner={stageVariant}>
					{#if step.calorie_mode && showCoach && !showingAnswerReveal && stageVariant}<aside
							class="studio-coach-aside"
						>
							<Coach pose="thinking" />
						</aside>{/if}
					<PriceTransition {products} stepId={step.id} transition={step.price_transition}>
						<!-- Stays mounted during a choice reveal so the next aisle sweep keeps these cards. -->
						<div
							hidden={choiceActive}
							class={`grid gap-4 ${productMode === 'compare' ? 'sm:grid-cols-2' : ''}`}
							class:price-stage-products={stageVariant}
							class:price-stage-single={stageVariant && productMode === 'guess'}
						>
							{#each products as product}{#if step.price_mode}<div class="product-display">
										<ProductCard {product} stage={stageVariant} />
										{#if step.price_mode && !showingAnswerReveal}<div class="price-shelf-label">
												<span>{$messages.priceStore.unknownPrice}</span><strong>— €</strong>
											</div>{/if}
									</div>{:else}<ProductCard {product} stage={stageVariant} />{/if}{/each}
						</div>
					</PriceTransition>
					{#if step.calorie_mode}<CalorieReveal
							{step}
							{showCoach}
							{players}
							choice={choiceActive}
							animate={animateChoice}
						/>{:else}<PriceReveal
							{step}
							{players}
							choice={choiceActive}
							animate={animateChoice}
						/>{/if}
				</div>
			</div>
		{/if}
		{#if step.body}
			<StepBodyMarkdown source={step.body} {stageVariant} />
		{/if}
		{#if !productMode}
			<div class={`question-card-media ${stageVariant ? 'question-card-media-stage' : ''}`}>
				{#if step.media?.type_ === 'image'}
					<ImageQuestionMedia {step} {stageVariant} />
				{:else if step.media?.type_ === 'audio'}
					<AudioQuestionMedia
						src={step.media.src}
						loop={step.media.loop}
						volume={step.media.volume ?? 1}
						{shouldPauseMedia}
						{shouldResumePausedMedia}
						playbackRevision={step.media.playback_revision ?? 0}
					/>
				{:else if step.media?.type_ === 'video'}
					<VideoQuestionMedia
						{step}
						{stageVariant}
						volume={step.media.volume ?? 1}
						{shouldPauseMedia}
						{shouldResumePausedMedia}
					/>
				{/if}
			</div>
		{/if}
		{#if showOptionGrid}
			<div
				class={`question-card-options grid gap-2 ${
					stageVariant
						? 'grid-cols-1 text-base sm:grid-cols-2 md:text-lg'
						: 'grid-cols-1 text-lg sm:grid-cols-2'
				}`}
			>
				{#each optionStates as optionState, optionIndex (optionIndex)}
					<div
						class={`option-flip ${showingAnswerReveal ? 'option-flip-revealed' : ''}`}
						style={`--option-delay: ${optionIndex * 90}ms`}
					>
						<div class="option-flip-inner">
							<div
								class={`option-face option-face-front ${
									stageVariant ? 'min-h-14 px-4 py-3' : 'min-h-16 px-4 py-4'
								}`}
							>
								<span class="option-text">{optionState.option}</span>
							</div>
							<div
								class={`option-face option-face-back ${
									optionState.correct ? 'option-face-correct' : 'option-face-wrong'
								} ${stageVariant ? 'min-h-14 px-4 py-3' : 'min-h-16 px-4 py-4'}`}
							>
								<span class="option-text">{optionState.option}</span>
								<span
									class={`option-points ${
										optionState.correct ? 'option-points-correct' : 'option-points-wrong'
									}`}
								>
									{optionState.pointsLabel}
								</span>
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
		{#if showOrderingList}
			<div
				class={`question-card-ordering grid gap-2 ${
					stageVariant ? 'text-base md:text-lg' : 'text-lg'
				} ${showingAnswerReveal ? 'question-card-ordering-revealed' : ''}`}
			>
				{#each orderingItems as item, itemIndex (orderingItemKey(orderingItems, item, itemIndex))}
					<div
						class={`ordering-display-row ${
							showingAnswerReveal ? 'ordering-display-row-revealed' : ''
						}`}
						animate:flip={{ duration: 420 }}
						style={`--ordering-delay: ${itemIndex * 85}ms`}
					>
						<span class="ordering-rank">#{itemIndex + 1}</span>
						<span class="ordering-text">{item}</span>
					</div>
				{/each}
			</div>
		{/if}
		{#if showInlineRevealedAnswer}
			<div
				class={`reveal-inline-pop question-card-status theme-soft-correct rounded-2xl border px-4 py-4 ${
					stageVariant ? 'text-xl md:text-3xl' : 'text-lg'
				}`}
			>
				<p class="theme-soft-correct-label text-sm font-black uppercase tracking-[0.22em]">
					{$messages.common.correctAnswer}
				</p>
				<p class="mt-2 font-extrabold leading-tight">
					{formatRevealValue(revealedAnswer?.value)}
				</p>
			</div>
		{:else if !showingAnswerReveal && revealedSubmission}
			<div
				class={`question-card-status theme-soft-primary rounded-2xl border px-4 py-3 ${
					stageVariant ? 'text-xl md:text-2xl' : 'text-lg'
				}`}
			>
				<span class="font-bold">{$messages.common.revealedAnswer}:</span>
				{String(revealedSubmission.value)}
			</div>
		{/if}
	{:else}
		<p class="theme-text-muted text-lg">{$messages.common.waitingForNextQuestion}</p>
	{/if}
</section>

<style lang="postcss">
	.question-card-stage {
		display: grid;
		grid-template-rows: auto auto auto minmax(0, 1fr) auto auto;
		gap: clamp(0.35rem, calc(0.8 * var(--stage-vh)), 0.75rem);
		height: 100%;
		min-height: 0;
		min-width: 0;
		padding: clamp(0.5rem, calc(1.1 * var(--stage-vw)), 1.25rem);
	}

	.question-card-stage.question-card-price-stage {
		/* Leave room for the product title, details, shelf label and spacing. */
		--product-image-height: clamp(
			7rem,
			min(calc(48 * var(--stage-vh)), calc(100cqh - 15rem)),
			44rem
		);
		grid-template-rows: auto minmax(0, 1fr);
	}
	.price-stage-content {
		container-type: size;
		display: flex;
		min-height: 0;
		overflow-y: auto;
	}
	.price-stage-inner {
		width: 100%;
		max-width: 96rem;
		margin: auto;
		padding-block: 1rem;
	}
	.price-stage-products {
		align-items: start;
	}
	.price-stage-single {
		max-width: 52rem;
		margin-inline: auto;
	}
	.question-card-stage.question-card-price-reveal {
		--product-image-height: clamp(8rem, calc(18 * var(--stage-vh)), 14rem);
	}

	/*
	 * The TV stage (1920x1080, watched from across the room). Nothing scrolls: product images take
	 * whatever height the text leaves, and the reveal puts the receipt in its own column.
	 */
	:global(.game-stage) .question-card-stage {
		gap: 1.25rem;
		padding: 0;
	}
	:global(.game-stage) .question-card-step-title {
		font-size: var(--tv-title);
		line-height: 1.05;
	}
	:global(.game-stage) .points-badge-stage {
		margin-top: 0.6rem;
		padding: 0.6rem 1.1rem;
		font-size: var(--tv-body);
	}
	:global(.game-stage) .price-stage-content {
		display: block;
		overflow: hidden;
	}
	:global(.game-stage) .price-stage-inner {
		display: grid;
		grid-template-rows: minmax(0, 1fr);
		height: 100%;
		margin: 0 auto;
		padding-block: 0;
	}
	:global(.game-stage) .price-stage-inner > :global(*) {
		min-width: 0;
		min-height: 0;
	}
	:global(.game-stage) .price-stage-inner :global(.price-transition),
	:global(.game-stage) .price-stage-inner :global(.price-transition > .incoming) {
		height: 100%;
	}
	:global(.game-stage) .price-stage-inner :global(.outgoing) {
		--product-image-height: 24rem;
	}
	:global(.game-stage) .price-stage-products {
		grid-template-rows: minmax(0, 1fr);
		align-items: stretch;
		gap: 2rem;
		height: 100%;
	}
	:global(.game-stage) .price-stage-single {
		max-width: 64rem;
	}
	:global(.game-stage) .price-stage-products > .product-display {
		display: flex;
		flex-direction: column;
		min-height: 0;
	}
	:global(.game-stage) .price-stage-products :global(.product-card) {
		flex: 1;
		min-height: 0;
	}
	/* Side by side, both cards reserve two lines of title and detail so their images line up. */
	:global(.game-stage) .price-stage-products:not(.price-stage-single) :global(.product-title) {
		min-height: 2.3em;
	}
	:global(.game-stage) .price-stage-products:not(.price-stage-single) :global(.product-detail) {
		display: -webkit-box;
		min-height: 2.4em;
	}
	/* The image grows into the height the title and labels leave. */
	:global(.game-stage) .price-stage-products :global(.product-card-stage > img),
	:global(.game-stage) .price-stage-products :global(.product-card-stage > div) {
		flex: 1 1 0;
		height: auto;
		min-height: 0;
	}
	/* Reveal: products (or the compare trays) on the left, the receipt in a column on the right. */
	:global(.game-stage) .question-card-price-reveal .price-stage-inner {
		grid-template-columns: minmax(0, 1fr) 40rem;
		gap: 2rem;
		max-width: none;
	}
	:global(.game-stage) .question-card-price-reveal .price-stage-inner > :global(*) {
		grid-row: 1;
		grid-column: 1;
	}
	:global(.game-stage) .question-card-price-reveal .price-stage-inner > :global(.price-receipt),
	:global(.game-stage) .question-card-price-reveal .price-stage-inner > :global(.calorie-reveal) {
		grid-column: 2;
		margin-top: 0;
		overflow: hidden;
	}
	/* Narrow rules are for phones; the fixed stage always keeps the wide layout. */
	@media (max-width: 639px) {
		.question-card-stage.question-card-price-stage:not(:global(.game-stage *)) {
			--product-image-height: clamp(7rem, calc(18 * var(--stage-vh)), 12rem);
		}
	}

	.question-card-stage-shell {
		position: relative;
		border-radius: 0;
		border: 0;
		background: transparent;
		box-shadow: none;
	}

	.question-card-reveal-pulse {
		animation: stage-reveal-pulse 620ms ease-out both;
	}

	.question-card-media-stage {
		display: grid;
		place-items: center;
		grid-row: 4;
		min-height: 0;
		min-width: 0;
		height: 100%;
		overflow: hidden;
	}

	.question-card-title-row {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: clamp(0.75rem, calc(2 * var(--stage-vw)), 1.5rem);
		min-width: 0;
	}

	.question-card-step-title {
		min-width: 0;
		overflow-wrap: anywhere;
	}

	.question-card-points-badge {
		flex: 0 0 auto;
		margin-top: 0.15rem;
		border-radius: 999px;
		border: 1px solid var(--party-soft-primary-border);
		background: var(--party-soft-primary-bg);
		color: var(--party-soft-primary-text);
		font-size: 0.82rem;
		font-weight: 950;
		line-height: 1;
		padding: 0.55rem 0.75rem;
		white-space: nowrap;
	}

	.points-badge-stage {
		margin-top: 0.35rem;
		font-size: clamp(0.9rem, calc(1.2 * var(--stage-vw)), 1.15rem);
		padding: 0.65rem 0.9rem;
	}

	.question-card-options {
		min-height: 0;
	}

	.question-card-ordering {
		min-height: 0;
		align-content: center;
	}

	.ordering-display-row {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		align-items: center;
		gap: 0.8rem;
		min-width: 0;
		border-radius: 1rem;
		border: 1px solid var(--party-border);
		background: color-mix(in srgb, var(--party-surface-strong), transparent 18%);
		box-shadow: 0 1px 2px rgb(15 23 42 / 0.08);
		padding: 0.72rem 0.9rem;
	}

	.ordering-display-row-revealed {
		border-color: var(--party-soft-primary-border);
		background: var(--party-soft-primary-bg);
		animation: ordering-reveal-land 520ms ease-out both;
		animation-delay: var(--ordering-delay);
	}

	.ordering-rank {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 3rem;
		border-radius: 999px;
		background: var(--party-muted-control);
		color: var(--party-ink);
		font-size: 0.8em;
		font-weight: 950;
		line-height: 1;
		padding: 0.45rem 0.65rem;
	}

	.ordering-display-row-revealed .ordering-rank {
		background: var(--party-primary-strong);
		color: white;
	}

	.ordering-text {
		min-width: 0;
		overflow-wrap: anywhere;
		font-weight: 900;
		line-height: 1.15;
		color: var(--party-ink);
	}

	.question-card-status {
		min-height: 0;
	}

	.option-flip {
		perspective: 56rem;
		min-width: 0;
	}

	.option-flip-inner {
		position: relative;
		display: grid;
		transform-style: preserve-3d;
		transition: transform 520ms cubic-bezier(0.2, 0.8, 0.2, 1);
		transition-delay: var(--option-delay);
	}

	.option-flip-revealed .option-flip-inner {
		transform: rotateX(180deg);
	}

	.option-flip-revealed .option-face-correct {
		animation: correct-answer-lift 560ms cubic-bezier(0.2, 0.9, 0.2, 1.2) both;
		animation-delay: calc(var(--option-delay) + 620ms);
	}

	.option-face {
		grid-area: 1 / 1;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		min-width: 0;
		border-radius: 1rem;
		border: 1px solid var(--party-border);
		background: color-mix(in srgb, var(--party-surface-strong), transparent 18%);
		color: var(--party-ink);
		box-shadow: 0 1px 2px rgb(15 23 42 / 0.08);
		backface-visibility: hidden;
	}

	.option-face-back {
		transform: rotateX(180deg);
	}

	.option-face-correct {
		border-color: var(--party-success-strong);
		background: var(--party-success);
		color: white;
		box-shadow: 0 10px 24px color-mix(in srgb, var(--party-success-strong), transparent 78%);
	}

	.option-face-wrong {
		border-color: var(--party-danger-strong);
		background: var(--party-danger);
		color: white;
		box-shadow: 0 10px 24px color-mix(in srgb, var(--party-danger-strong), transparent 78%);
	}

	.option-text {
		min-width: 0;
		overflow-wrap: anywhere;
		font-weight: 900;
		line-height: 1.15;
	}

	.option-points {
		flex: 0 0 auto;
		border-radius: 999px;
		opacity: 0;
		padding: 0.35rem 0.65rem;
		font-size: 0.78em;
		font-weight: 950;
		line-height: 1;
	}

	.option-flip-revealed .option-points {
		animation: points-badge-pop 340ms cubic-bezier(0.2, 0.9, 0.2, 1.25) both;
		animation-delay: calc(var(--option-delay) + 500ms);
	}

	.option-points-correct {
		background: var(--party-success-strong);
		color: white;
	}

	.option-points-wrong {
		background: var(--party-danger-strong);
		color: white;
	}

	.reveal-inline-pop {
		animation: answer-card-pop 480ms cubic-bezier(0.2, 0.9, 0.2, 1.2) both;
	}

	@keyframes stage-reveal-pulse {
		0% {
			box-shadow: 0 0 0 rgb(14 165 233 / 0);
			transform: scale(1);
		}

		42% {
			box-shadow: 0 0 38px rgb(14 165 233 / 0.22);
			transform: scale(1.006);
		}

		100% {
			box-shadow: 0 0 0 rgb(14 165 233 / 0);
			transform: scale(1);
		}
	}

	@keyframes points-badge-pop {
		0% {
			opacity: 0;
			transform: translateX(0.35rem) scale(0.72);
		}

		68% {
			opacity: 1;
			transform: translateX(0) scale(1.12);
		}

		100% {
			opacity: 1;
			transform: translateX(0) scale(1);
		}
	}

	@keyframes ordering-reveal-land {
		0% {
			filter: brightness(1);
			box-shadow: 0 1px 2px rgb(15 23 42 / 0.08);
		}

		48% {
			filter: brightness(1.06);
			box-shadow: 0 0 24px color-mix(in srgb, var(--party-primary-strong), transparent 80%);
		}

		100% {
			filter: brightness(1);
			box-shadow: 0 1px 2px rgb(15 23 42 / 0.08);
		}
	}

	@keyframes correct-answer-lift {
		0%,
		100% {
			filter: brightness(1);
			transform: rotateX(180deg) translateY(0);
		}

		48% {
			filter: brightness(1.1);
			transform: rotateX(180deg) translateY(-0.18rem);
		}
	}

	@keyframes answer-card-pop {
		0% {
			opacity: 0;
			transform: translateY(0.4rem) scale(0.96);
			box-shadow: 0 0 0 rgb(16 185 129 / 0);
		}

		62% {
			opacity: 1;
			transform: translateY(0) scale(1.018);
			box-shadow: 0 0 30px rgb(16 185 129 / 0.25);
		}

		100% {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.question-card-reveal-pulse,
		.option-flip-revealed .option-face-correct,
		.option-flip-revealed .option-points,
		.ordering-display-row-revealed,
		.reveal-inline-pop {
			animation: none;
		}

		.option-points {
			opacity: 1;
		}

		.option-flip-inner {
			transform-style: flat;
			transition: none;
		}

		.option-flip-revealed .option-flip-inner {
			transform: none;
		}

		.option-face {
			backface-visibility: visible;
		}

		.option-face-front {
			opacity: 1;
		}

		.option-flip-revealed .option-face-front {
			opacity: 0;
		}

		.option-face-back {
			opacity: 0;
			transform: none;
		}

		.option-flip-revealed .option-face-back {
			opacity: 1;
		}
	}
</style>
