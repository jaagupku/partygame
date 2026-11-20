<script lang="ts">
	import { messages } from '#lib/i18n.js';
	let { product, stage = false }: { product: PriceCard | CalorieCard; stage?: boolean } = $props();
	let failed = $state(false);
	$effect(() => {
		product.image_url;
		failed = false;
	});
</script>

<div
	class="product-card flex h-full min-w-0 flex-col items-center gap-3"
	class:product-card-stage={stage}
>
	{#if failed}
		<div
			class="theme-surface-muted flex h-40 w-full items-center justify-center rounded-xl p-4 text-sm"
		>
			{$messages.priceGame.imageUnavailable}
		</div>
	{:else}
		<img
			src={product.image_url}
			alt={product.title}
			class="h-40 w-full rounded-xl bg-white object-contain p-2 sm:h-52"
			onerror={() => (failed = true)}
		/>
	{/if}
	<p class="product-title text-center text-lg font-bold leading-snug">{product.title}</p>
	{#if 'basis' in product}<p class="nutrition-basis font-bold">
			{$messages.calorieGame[product.basis === '100ml' ? 'per100ml' : 'per100g']}
		</p>{/if}
	{#if product.detail && !product.title.includes(product.detail)}<p
			class="product-detail theme-text-muted text-center text-sm"
		>
			{product.detail}
		</p>{:else if stage}<p class="product-detail" aria-hidden="true"></p>{/if}
</div>

<style>
	.product-card-stage img,
	.product-card-stage > div {
		height: var(--product-image-height, clamp(12rem, calc(36 * var(--stage-vh)), 28rem));
		flex-shrink: 0;
	}
	.product-card-stage > p {
		font-size: clamp(1.1rem, calc(1.5 * var(--stage-vw)), 1.65rem);
	}
	/* The TV stage: read from across the room; long titles and details keep to two lines.
	   (An empty detail line lets side-by-side cards reserve equal room, so their images align.) */
	:global(.game-stage) .product-card-stage > p {
		flex-shrink: 0;
		font-size: var(--tv-body);
		line-height: 1.2;
	}
	:global(.game-stage) .product-card-stage > .product-title {
		font-size: var(--tv-subtitle);
		line-height: 1.15;
	}
	:global(.game-stage) .product-card-stage > .product-title,
	:global(.game-stage) .product-card-stage > .product-detail {
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		overflow: hidden;
	}
	:global(.game-stage) .product-card-stage > .product-detail:empty {
		display: none;
	}
</style>
