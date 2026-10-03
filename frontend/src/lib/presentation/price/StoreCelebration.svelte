<script lang="ts">
	let { stage }: { stage: string } = $props();
</script>

{#key stage}
	<div class="store-celebration" aria-hidden="true">
		<img src="/presentation/price/shopping-bag.svg" alt="" />
		<img src="/presentation/price/shopping-bag.svg" alt="" />
		{#each Array.from({ length: 18 }, (_, i) => i) as i}
			<span style={`--x:${(i * 37) % 100}%;--delay:${(i % 5) * 70}ms;--tilt:${i * 41}deg`}></span>
		{/each}
	</div>
{/key}

<style>
	.store-celebration {
		position: absolute;
		inset: 0;
		overflow: hidden;
		pointer-events: none;
	}
	img {
		position: absolute;
		width: clamp(5rem, 12vw, 12rem);
		bottom: 1rem;
		left: 1rem;
		transform: rotate(-12deg);
		opacity: 0.5;
	}
	img:nth-child(2) {
		left: auto;
		right: 1rem;
		transform: rotate(12deg);
	}
	span {
		position: absolute;
		top: -2rem;
		left: var(--x);
		width: 0.6rem;
		height: 1.4rem;
		background: #efbb45;
		animation: store-paper 1800ms ease-out var(--delay) both;
	}
	span:nth-child(3n) {
		background: #17665b;
	}
	span:nth-child(3n + 1) {
		background: #fffdf7;
		border: 1px solid #c6b68c;
	}
	@keyframes store-paper {
		from {
			transform: translateY(0) rotate(0);
			opacity: 1;
		}
		to {
			transform: translateY(65vh) rotate(var(--tilt));
			opacity: 0;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		span {
			display: none;
		}
	}
</style>
