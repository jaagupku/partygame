<script lang="ts">
	let { stage }: { stage: string } = $props();
	const marks = ['star', 'squiggle', 'heart', 'star', 'spiral', 'squiggle'] as const;
	const paths: Record<(typeof marks)[number], string> = {
		star: 'M20 2 l5 11 l12 2 l-9 8 l3 12 l-11 -6 l-11 6 l3 -12 l-9 -8 l12 -2 z',
		squiggle: 'M2 20 c6 -12 12 12 18 0 s12 12 18 0',
		heart: 'M20 34 c-16 -10 -18 -22 -10 -26 c5 -3 10 0 10 5 c0 -5 5 -8 10 -5 c8 4 6 16 -10 26 z',
		spiral: 'M20 20 c0 -4 6 -4 6 0 c0 8 -12 8 -12 0 c0 -12 18 -12 18 0 c0 16 -24 16 -24 0'
	};
</script>

{#key stage}
	<div class="sketch-celebration" aria-hidden="true">
		{#each Array.from({ length: 14 }, (_, i) => i) as i}
			{@const mark = marks[i % marks.length]}
			<svg
				viewBox="0 0 40 40"
				class:sketch-coral={i % 2 === 1}
				style={`--x:${(i * 29 + 7) % 96}%;--y:${(i * 41 + 11) % 92}%;--turn:${((i * 37) % 50) - 25}deg;--delay:${i * 45}ms`}
			>
				<path d={paths[mark]} />
			</svg>
		{/each}
	</div>
{/key}

<style>
	.sketch-celebration {
		position: absolute;
		inset: 0;
		overflow: hidden;
		pointer-events: none;
	}
	svg {
		position: absolute;
		left: var(--x);
		top: var(--y);
		width: 2.75rem;
		fill: none;
		stroke: #2a4a9b;
		stroke-width: 3;
		stroke-linecap: round;
		stroke-linejoin: round;
		opacity: 0.3;
		rotate: var(--turn);
		animation: sketch-doodle 600ms ease-out var(--delay) both;
	}
	.sketch-coral {
		stroke: #f26b5b;
	}
	@keyframes sketch-doodle {
		from {
			opacity: 0;
			scale: 0.4;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		svg {
			animation: none;
		}
	}
</style>
