<script lang="ts">
	import { messages } from '$lib/i18n';
	import { drawingText } from './helpers';
	let { view }: { view: DrawingGameView } = $props();
	// The server sends no criterion during the showcase, so the sealed card cannot leak it.
	const criterion = $derived(view.matchup?.criterion ?? null);
	const twist = $derived(view.phase === 'criterion_reveal');
</script>

{#if criterion === null}
	<div class="drawing-criterion drawing-criterion-sealed">
		<span class="drawing-criterion-label">{$messages.drawingMashup.criterion}</span>
		<span class="drawing-criterion-seal" aria-hidden="true">?</span>
		<span class="drawing-criterion-text">{$messages.drawingMashup.criterionSecret}</span>
	</div>
{:else}
	<div class="drawing-criterion" class:drawing-twist={twist} role="status" aria-live="polite">
		{#if twist}<span class="drawing-twist-burst">{$messages.drawingMashup.plotTwist}</span>{/if}
		<span class="drawing-criterion-label">{$messages.drawingMashup.criterion}</span>
		<strong class="drawing-criterion-text"
			>{drawingText(criterion, 'criterion', view.language)}</strong
		>
	</div>
{/if}

<style>
	.drawing-criterion {
		position: relative;
		display: grid;
		justify-items: start;
		align-content: center;
		gap: 0.2rem;
		/* Reserved height: revealing the criterion must not push the artwork down. */
		min-height: 7.75rem;
		padding: 0.75rem 1rem;
		border: 2px solid var(--party-border);
		border-radius: 0.75rem;
		background: var(--party-surface);
		transition:
			background-color 500ms ease-out,
			border-color 500ms ease-out,
			color 500ms ease-out;
	}
	.drawing-criterion-label {
		font-size: 0.8rem;
		font-weight: 800;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		opacity: 0.75;
	}
	.drawing-criterion-text {
		font-size: clamp(1.15rem, 2.4vw, 2rem);
		line-height: 1.2;
		overflow-wrap: anywhere;
	}
	.drawing-criterion-sealed {
		grid-template-columns: auto 1fr;
		align-items: center;
		column-gap: 0.85rem;
		border-style: dashed;
	}
	.drawing-criterion-sealed .drawing-criterion-label {
		grid-column: 2;
	}
	.drawing-criterion-sealed .drawing-criterion-text {
		grid-column: 2;
		font-size: 1rem;
		font-weight: 700;
		opacity: 0.8;
	}
	.drawing-criterion-seal {
		grid-row: 1 / span 2;
		display: grid;
		place-items: center;
		width: 2.75rem;
		height: 2.75rem;
		border-radius: 999px;
		background: var(--party-accent);
		color: var(--party-ink);
		font-size: 1.6rem;
		font-weight: 900;
		animation: drawing-seal-wobble 1.6s ease-in-out infinite;
	}
	.drawing-twist {
		animation: drawing-twist-in 520ms cubic-bezier(0.2, 1.4, 0.4, 1) both;
	}
	.drawing-twist .drawing-criterion-text {
		animation: drawing-twist-text 420ms 180ms ease-out both;
	}
	.drawing-twist-burst {
		position: absolute;
		top: -1.1rem;
		right: 1rem;
		padding: 0.25rem 0.85rem;
		border: 3px solid var(--party-ink);
		border-radius: 0.4rem;
		background: var(--party-accent);
		color: var(--party-ink);
		font-family: var(--presentation-heading-font);
		font-size: 1.1rem;
		font-weight: 900;
		text-transform: uppercase;
		transform: rotate(-4deg);
		animation: drawing-burst 480ms cubic-bezier(0.2, 1.6, 0.4, 1) both;
	}
	@keyframes drawing-seal-wobble {
		50% {
			transform: rotate(-8deg) scale(1.06);
		}
	}
	@keyframes drawing-twist-in {
		from {
			transform: scale(0.9) rotate(-1.5deg);
			opacity: 0;
		}
	}
	@keyframes drawing-twist-text {
		from {
			transform: translateY(0.5rem);
			opacity: 0;
		}
	}
	@keyframes drawing-burst {
		from {
			transform: rotate(-30deg) scale(0.2);
			opacity: 0;
		}
	}
	/* Pause holds the transformation wherever it is. */
	:global(.drawing-stage-paused) .drawing-criterion,
	:global(.drawing-stage-paused) .drawing-criterion * {
		animation-play-state: paused;
	}
	@media (prefers-reduced-motion: reduce) {
		.drawing-criterion,
		.drawing-criterion * {
			animation: none;
			transition: none;
		}
	}
</style>
