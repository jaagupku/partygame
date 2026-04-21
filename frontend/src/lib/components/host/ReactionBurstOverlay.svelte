<script lang="ts">
	interface DisplayReaction {
		instanceId: string;
		reaction: string;
		xPercent: number;
		driftX: number;
		sizeRem: number;
		rotationDeg: number;
		durationMs: number;
		delayMs: number;
	}

	interface ReactionBurstOverlayProps {
		reactions: DisplayReaction[];
		label: string;
	}

	let { reactions, label }: ReactionBurstOverlayProps = $props();
</script>

<div class="reaction-overlay" aria-label={label}>
	{#each reactions as item (item.instanceId)}
		<div
			class="reaction-burst"
			aria-hidden="true"
			style={`left:${item.xPercent}%;--reaction-drift-x:${item.driftX}px;--reaction-rotation:${item.rotationDeg}deg;--reaction-duration:${item.durationMs}ms;--reaction-delay:${item.delayMs}ms;font-size:${item.sizeRem}rem;`}
		>
			<span>{item.reaction}</span>
		</div>
	{/each}
</div>

<style>
	.reaction-overlay {
		pointer-events: none;
		position: absolute;
		inset: 0;
		overflow: hidden;
		z-index: 4;
	}

	.reaction-burst {
		position: absolute;
		bottom: -12%;
		will-change: transform, opacity;
		animation: reaction-float var(--reaction-duration) ease-out var(--reaction-delay) forwards;
		filter: drop-shadow(0 10px 18px rgba(15, 23, 42, 0.18));
		line-height: 1;
		user-select: none;
	}

	.reaction-burst span {
		display: block;
	}

	@keyframes reaction-float {
		0% {
			opacity: 0;
			transform: translate(-50%, 0) rotate(var(--reaction-rotation)) scale(0.82);
		}

		12% {
			opacity: 1;
		}

		100% {
			opacity: 0;
			transform: translate(calc(-50% + var(--reaction-drift-x)), -120vh)
				rotate(calc(var(--reaction-rotation) + 18deg)) scale(1.12);
		}
	}
</style>
