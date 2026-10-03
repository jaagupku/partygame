<script lang="ts">
	import { untrack, type Snippet } from 'svelte';
	import ProductCard from '$lib/components/prices/ProductCard.svelte';
	import { createPriceTransitionClock } from './transition-clock';
	let {
		products,
		stepId,
		transition,
		phone = false,
		children
	}: {
		products: PriceCard[];
		stepId: string;
		transition?: PriceTransitionState | null;
		phone?: boolean;
		children: Snippet;
	} = $props();
	let previous: PriceCard[] = [];
	let previousKey = '';
	let outgoing = $state<PriceCard[]>([]);
	let elapsed = $state(600);
	const clock = createPriceTransitionClock();
	const moving = $derived(Boolean(transition && elapsed < transition.duration_ms));
	$effect.pre(() => {
		const key = stepId;
		if (key !== previousKey) {
			outgoing = transition && !phone ? previous : [];
			previous = products;
			previousKey = key;
		}
	});
	$effect(() => {
		const value = transition;
		if (!value) {
			outgoing = [];
			elapsed = 600;
			return;
		}
		elapsed = untrack(() => clock.sync(value, performance.now()));
		let frame = 0;
		const tick = () => {
			elapsed = clock.read(performance.now());
			if (elapsed < value.duration_ms) frame = requestAnimationFrame(tick);
			else outgoing = [];
		};
		frame = requestAnimationFrame(tick);
		return () => cancelAnimationFrame(frame);
	});
</script>

<div
	class="price-transition"
	class:moving
	class:phone
	style:--travel-elapsed={`${elapsed}ms`}
	style:--travel-duration={`${transition?.duration_ms ?? 600}ms`}
	data-price-transition={moving ? transition?.id : undefined}
>
	<div class="incoming">{@render children()}</div>
	{#if moving && !phone}
		<div class="aisle-shelves" aria-hidden="true"><i></i><i></i><i></i></div>
		{#if outgoing.length}
			<div class="outgoing" class:comparison={outgoing.length > 1} aria-hidden="true" inert>
				{#each outgoing as product}<div class="departing-product">
						<ProductCard {product} stage />
					</div>{/each}
			</div>
		{/if}
	{/if}
</div>

<style>
	.price-transition {
		position: relative;
		min-width: 0;
	}
	.moving {
		overflow: clip;
	}
	.moving .incoming,
	.outgoing,
	.aisle-shelves {
		animation-duration: var(--travel-duration);
		animation-delay: calc(-1 * var(--travel-elapsed));
		animation-fill-mode: both;
		animation-play-state: paused;
		animation-timing-function: cubic-bezier(0.2, 0.8, 0.2, 1);
	}
	.moving .incoming {
		animation-name: product-arrive;
		transform-origin: center bottom;
	}
	.outgoing {
		--product-image-height: clamp(8rem, 18vh, 14rem);
		position: absolute;
		inset: 0;
		display: grid;
		gap: 1rem;
		pointer-events: none;
		animation-name: product-depart;
	}
	.departing-product {
		min-width: 0;
		width: 100%;
		max-width: 38rem;
		margin-inline: auto;
		padding: 1rem;
		background: #f3eddf;
		border: 1px solid #ded9c8;
		border-radius: 0.5rem;
	}
	.aisle-shelves {
		position: absolute;
		inset: 0;
		display: flex;
		justify-content: space-around;
		gap: 10%;
		pointer-events: none;
		animation-name: aisle-pass;
	}
	.aisle-shelves i {
		display: block;
		width: 24%;
		border-inline: 8px solid #17665b;
		background: repeating-linear-gradient(
			to bottom,
			transparent 0 26%,
			#e0d4b8 26% 28%,
			#17665b 28% 30%,
			transparent 30% 33%
		);
	}
	.phone.moving .incoming {
		animation: none;
	}
	.phone.moving .incoming :global(.product-card) {
		animation: phone-arrive var(--travel-duration) ease-out both paused;
		animation-delay: calc(-1 * var(--travel-elapsed));
	}
	@media (min-width: 640px) {
		.comparison {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@keyframes product-depart {
		0% {
			opacity: 1;
			transform: translateX(0);
		}
		30%,
		100% {
			opacity: 0;
			transform: translateX(-12%);
		}
	}
	@keyframes aisle-pass {
		0% {
			opacity: 0;
			transform: translateX(65%);
		}
		18% {
			opacity: 0.55;
		}
		60%,
		100% {
			opacity: 0;
			transform: translateX(-65%);
		}
	}
	@keyframes product-arrive {
		0%,
		30% {
			opacity: 0;
			transform: translate(40px, 8px) scale(0.96) rotate(-1.5deg);
		}
		65% {
			opacity: 1;
			transform: translate(0, -5px) scale(1) rotate(0);
		}
		100% {
			opacity: 1;
			transform: translate(0, 0) scale(1) rotate(0);
		}
	}
	@keyframes phone-arrive {
		0% {
			opacity: 0.35;
			transform: translateX(12px);
		}
		100% {
			opacity: 1;
			transform: translateX(0);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.moving .incoming,
		.phone.moving .incoming :global(.product-card) {
			animation: none;
		}
		.outgoing,
		.aisle-shelves {
			display: none;
		}
	}
</style>
