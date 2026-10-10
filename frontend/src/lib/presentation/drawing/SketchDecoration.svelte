<script lang="ts">
	import { messages } from '$lib/i18n';
	import type { DecorationSurface } from '../registry';
	let { variant, surface }: { variant: string; surface: DecorationSurface } = $props();
</script>

{#if surface === 'preview'}
	<div class="sketch-illustration" aria-hidden="true">
		<img src="/presentation/drawing/sketchbook.svg" alt="" width="720" height="300" />
	</div>
{:else if surface === 'screen' && variant === 'welcome'}
	<div class="sketch-welcome">
		<p class="sketch-eyebrow">{$messages.drawingSketchbook.welcome}</p>
		<img src="/presentation/drawing/sketchbook.svg" alt="" width="720" height="300" />
	</div>
{:else}
	<!-- Paper underneath; the judging stage wipes in over it, never over the artwork. -->
	<div
		class="sketch-backdrop"
		class:sketch-judging={variant === 'judging'}
		class:sketch-phone={surface === 'controller'}
		aria-hidden="true"
	>
		<svg class="sketch-doodle sketch-doodle-top" viewBox="0 0 220 120">
			<path d="M10 60 c20 -30 40 30 60 0 s40 30 60 0 s40 30 60 0" />
			<path d="M40 100 l14 -14 m-14 0 l14 14" class="sketch-coral" />
			<circle cx="180" cy="28" r="14" />
		</svg>
		<svg class="sketch-doodle sketch-doodle-bottom" viewBox="0 0 220 140">
			<path d="M120 20 l10 22 l24 3 l-18 16 l5 24 l-21 -12 l-21 12 l5 -24 l-18 -16 l24 -3 z" />
			<path d="M20 110 c0 -30 50 -30 50 0 c0 20 -30 20 -30 0" class="sketch-coral" />
			<path d="M170 120 h40 M176 104 h30" />
		</svg>
		<div class="sketch-stage">
			<span class="sketch-spot sketch-spot-left"></span>
			<span class="sketch-spot sketch-spot-right"></span>
			<img class="sketch-twist" src="/presentation/drawing/plot-twist.svg" alt="" />
		</div>
	</div>
{/if}

<style>
	.sketch-illustration img,
	.sketch-welcome img {
		display: block;
		width: 100%;
		height: clamp(7rem, 16vw, 11rem);
		object-fit: contain;
	}
	.sketch-welcome {
		width: min(36rem, 100%);
		margin: 0 auto 1rem;
	}
	.sketch-welcome img {
		height: clamp(9rem, 28vh, 18rem);
	}
	.sketch-eyebrow {
		margin: 0 0 0.25rem;
		color: #f26b5b;
		font-family: var(--presentation-heading-font);
		font-size: clamp(1.6rem, 3vw, 2.4rem);
		font-weight: 700;
		text-align: center;
		transform: rotate(-2deg);
	}
	.sketch-backdrop {
		position: fixed;
		inset: 0;
		z-index: -1;
		overflow: hidden;
		pointer-events: none;
	}
	.sketch-doodle {
		position: absolute;
		width: clamp(7rem, 16vw, 14rem);
		fill: none;
		stroke: #2a4a9b;
		stroke-width: 4;
		stroke-linecap: round;
		stroke-linejoin: round;
		opacity: 0.22;
	}
	.sketch-doodle .sketch-coral {
		stroke: #f26b5b;
	}
	/* Doodles stay in the margins below the content, clear of headings and counters. */
	.sketch-doodle-top {
		bottom: 1rem;
		left: 1rem;
	}
	.sketch-doodle-bottom {
		right: 1rem;
		bottom: 1rem;
	}
	.sketch-stage {
		position: absolute;
		inset: 0;
		background:
			radial-gradient(ellipse at 50% 110%, #ffd23f33 0 30%, transparent 60%),
			repeating-conic-gradient(from 0deg at 50% -10%, #4b1c8c 0 6deg, #3b1470 6deg 12deg);
		clip-path: circle(0% at 50% 45%);
		transition: clip-path 650ms cubic-bezier(0.65, 0, 0.25, 1);
	}
	.sketch-judging .sketch-stage {
		clip-path: circle(150% at 50% 45%);
	}
	.sketch-spot {
		position: absolute;
		top: -20%;
		width: 45vw;
		height: 140%;
		background: linear-gradient(to bottom, #fff6c855, transparent 80%);
		clip-path: polygon(45% 0, 55% 0, 100% 100%, 0 100%);
	}
	.sketch-spot-left {
		left: -8vw;
		transform: rotate(-18deg);
	}
	.sketch-spot-right {
		right: -8vw;
		transform: rotate(18deg);
	}
	.sketch-twist {
		position: absolute;
		right: 1.5rem;
		bottom: 1.5rem;
		width: clamp(6rem, 12vw, 12rem);
		opacity: 0;
		transform: rotate(12deg) scale(0.3);
		transition:
			opacity 200ms ease-out 250ms,
			transform 450ms cubic-bezier(0.2, 1.6, 0.4, 1) 250ms;
	}
	.sketch-judging .sketch-twist {
		opacity: 0.9;
		transform: rotate(12deg) scale(1);
	}
	.sketch-phone .sketch-doodle {
		width: 6rem;
		opacity: 0.16;
	}
	.sketch-phone .sketch-twist {
		bottom: 1rem;
		width: 4.5rem;
		opacity: 0;
	}
	.sketch-phone.sketch-judging .sketch-twist {
		opacity: 0.5;
	}
	@media (prefers-reduced-motion: reduce) {
		.sketch-stage,
		.sketch-twist {
			transition: none;
		}
	}
</style>
