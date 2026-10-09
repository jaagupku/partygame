<script lang="ts">
	let { stage }: { stage: string } = $props();
</script>

{#key stage}
	<div class="studio-celebration" aria-hidden="true">
		{#each Array.from({ length: 12 }, (_, i) => i) as i}
			<span style={`--x:${(i * 29) % 100}%;--y:${(i * 37) % 100}%;--delay:${i * 35}ms`}></span>
		{/each}
	</div>
{/key}

<style>
	.studio-celebration {
		position: absolute;
		inset: 0;
		overflow: hidden;
		pointer-events: none;
	}
	span {
		position: absolute;
		left: var(--x);
		top: var(--y);
		width: 3rem;
		height: 1rem;
		border-radius: 1rem;
		background: #ed806d;
		opacity: 0.18;
		transform: rotate(-35deg);
		animation: studio-spark 700ms ease-out var(--delay) both;
	}
	span:nth-child(2n) {
		background: #37c3b5;
		border-radius: 50%;
		width: 2rem;
		height: 2rem;
	}
	@keyframes studio-spark {
		from {
			opacity: 0;
			scale: 0.5;
			translate: 0 1rem;
		}
		to {
			opacity: 0.18;
			scale: 1;
			translate: 0 0;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		span {
			animation: none;
		}
	}
</style>
