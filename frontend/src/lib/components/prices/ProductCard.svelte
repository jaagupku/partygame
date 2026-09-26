<script lang="ts">
	import { messages } from '$lib/i18n';
	let { product, stage = false }: { product: PriceCard; stage?: boolean } = $props();
	let failed = $state(false);
	$effect(() => {
		product.image_url;
		failed = false;
	});
</script>

<div class="flex h-full min-w-0 flex-col items-center gap-3" class:product-card-stage={stage}>
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
	<p class="text-center text-lg font-bold leading-snug">{product.title}</p>
	{#if product.detail && !product.title.includes(product.detail)}<p
			class="theme-text-muted text-center text-sm"
		>
			{product.detail}
		</p>{/if}
</div>

<style>
	.product-card-stage img,
	.product-card-stage > div {
		height: var(--product-image-height, clamp(12rem, 36vh, 28rem));
		flex-shrink: 0;
	}
	.product-card-stage > p {
		font-size: clamp(1.1rem, 1.5vw, 1.65rem);
	}
</style>
