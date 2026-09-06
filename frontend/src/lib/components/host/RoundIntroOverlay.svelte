<script lang="ts">
	import { browser } from '$app/environment';
	import { messages } from '$lib/i18n';
	import { tick } from 'svelte';

	interface RoundIntroOverlayProps {
		round?: RuntimeRoundState;
		persistent?: boolean;
	}

	let { round, persistent = false }: RoundIntroOverlayProps = $props();

	let visibleRound = $state<RuntimeRoundState | undefined>(undefined);
	let lastRoundId = $state<string | undefined>(undefined);
	let visible = $state(false);
	let hideTimeoutId = $state<number | null>(null);
	let contentElement = $state<HTMLDivElement>();
	let titleElement = $state<HTMLHeadingElement>();
	let titleFontSize = $state('');
	let titleResizeObserver: ResizeObserver | undefined;

	const variants = ['pop', 'slide', 'shimmer', 'flip'] as const;
	type AnimationVariant = (typeof variants)[number];

	const roundTitle = $derived(
		visibleRound?.title?.trim() ||
			$messages.editor.history.fallbackRoundLabel(visibleRound?.number ?? 1)
	);
	const roundMeta = $derived(
		visibleRound
			? `${$messages.editor.history.fallbackRoundLabel(visibleRound.number)} / ${visibleRound.total}`
			: ''
	);
	const animationVariant = $derived(getAnimationVariant(visibleRound));

	$effect(() => {
		if (!round || round.id === lastRoundId) {
			return;
		}
		lastRoundId = round.id;
		visibleRound = round;
		visible = true;

		if (hideTimeoutId !== null) {
			window.clearTimeout(hideTimeoutId);
			hideTimeoutId = null;
		}
		if (!persistent && browser) {
			hideTimeoutId = window.setTimeout(() => {
				visible = false;
				hideTimeoutId = null;
			}, 2800);
		}
	});

	$effect(() => {
		return () => {
			if (hideTimeoutId !== null) {
				window.clearTimeout(hideTimeoutId);
				hideTimeoutId = null;
			}
			titleResizeObserver?.disconnect();
		};
	});

	$effect(() => {
		roundTitle;
		visibleRound;
		void fitTitleToSingleLine();
	});

	$effect(() => {
		if (!browser || !contentElement) {
			return;
		}
		titleResizeObserver?.disconnect();
		titleResizeObserver = new ResizeObserver(() => {
			void fitTitleToSingleLine();
		});
		titleResizeObserver.observe(contentElement);
		let cancelled = false;
		void document.fonts?.ready.then(() => {
			if (!cancelled) void fitTitleToSingleLine();
		});
		return () => {
			cancelled = true;
			titleResizeObserver?.disconnect();
			titleResizeObserver = undefined;
		};
	});

	function getAnimationVariant(activeRound?: RuntimeRoundState): AnimationVariant {
		if (!activeRound) {
			return 'pop';
		}
		const seed = `${activeRound.id}:${activeRound.number}`;
		let hash = 0;
		for (let index = 0; index < seed.length; index += 1) {
			hash = (hash * 31 + seed.charCodeAt(index)) >>> 0;
		}
		return variants[hash % variants.length];
	}

	function preferredTitleFontSizePx() {
		if (!browser) {
			return 54;
		}
		const rootFontSize =
			Number.parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
		return Math.min(Math.max(3.4 * rootFontSize, window.innerWidth * 0.1), 9.5 * rootFontSize);
	}

	async function fitTitleToSingleLine() {
		if (!browser || !titleElement || !contentElement) {
			return;
		}
		await tick();
		if (!titleElement || !contentElement) {
			return;
		}

		const contentStyle = getComputedStyle(contentElement);
		const availableWidth =
			contentElement.clientWidth -
			Number.parseFloat(contentStyle.paddingLeft) -
			Number.parseFloat(contentStyle.paddingRight);
		if (availableWidth <= 0) {
			return;
		}

		let low = 4;
		let high = preferredTitleFontSizePx();
		for (let step = 0; step < 12; step += 1) {
			const midpoint = (low + high) / 2;
			titleElement.style.fontSize = `${midpoint}px`;
			if (titleElement.scrollWidth <= availableWidth) {
				low = midpoint;
			} else {
				high = midpoint;
			}
		}
		titleElement.style.fontSize = `${low}px`;
		if (titleElement.scrollWidth > availableWidth) {
			low = Math.max(4, low * (availableWidth / titleElement.scrollWidth));
		}
		titleFontSize = `${Math.floor(low)}px`;
	}
</script>

{#if visibleRound}
	<div
		class={`round-intro-overlay ${visible ? 'round-intro-visible' : 'round-intro-hidden'} variant-${animationVariant}`}
		aria-live="polite"
		aria-atomic="true"
	>
		<div class="round-intro-content" bind:this={contentElement}>
			<p class="round-intro-kicker">{roundMeta}</p>
			<h2 class="round-intro-title" style:font-size={titleFontSize} bind:this={titleElement}>
				{roundTitle}
			</h2>
		</div>
	</div>
{/if}

<style>
	.round-intro-overlay {
		pointer-events: none;
		position: absolute;
		inset: 0;
		z-index: 8;
		display: grid;
		place-items: center;
		padding: clamp(1rem, 4vw, 4rem);
		opacity: 0;
		transition: opacity 360ms ease;
	}

	.round-intro-visible {
		opacity: 1;
	}

	.round-intro-hidden {
		opacity: 0;
	}

	.round-intro-content {
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		width: min(68rem, 100%);
		min-width: 0;
		justify-items: center;
		gap: 0.8rem;
		border-radius: 0.5rem;
		background:
			linear-gradient(135deg, rgb(15 23 42 / 0.9), rgb(30 41 59 / 0.84)),
			radial-gradient(circle at 20% 0%, rgb(56 189 248 / 0.38), transparent 36%),
			radial-gradient(circle at 82% 18%, rgb(251 191 36 / 0.34), transparent 32%);
		padding: clamp(1.5rem, 4.5vw, 4.5rem) clamp(1.7rem, 6vw, 6rem);
		text-align: center;
		color: white;
		box-shadow: 0 32px 80px rgb(15 23 42 / 0.34);
		overflow: hidden;
	}

	.round-intro-content::before,
	.round-intro-content::after {
		content: '';
		position: absolute;
		inset: 0;
		pointer-events: none;
	}

	.round-intro-content::before {
		background: linear-gradient(
			110deg,
			transparent 0 34%,
			rgb(255 255 255 / 0.22) 46%,
			transparent 58%
		);
		transform: translateX(-120%);
	}

	.round-intro-content::after {
		border: 1px solid rgb(255 255 255 / 0.2);
		border-radius: inherit;
	}

	.round-intro-kicker {
		position: relative;
		z-index: 1;
		font-size: clamp(0.9rem, 1.4vw, 1.25rem);
		font-weight: 950;
		text-transform: uppercase;
		letter-spacing: 0.18em;
		color: rgb(191 219 254);
	}

	.round-intro-title {
		position: relative;
		z-index: 1;
		width: 100%;
		min-width: 0;
		max-width: 100%;
		white-space: nowrap;
		font-size: clamp(3.4rem, 10vw, 9.5rem);
		font-weight: 1000;
		line-height: 0.94;
		letter-spacing: 0;
		text-shadow: 0 16px 34px rgb(0 0 0 / 0.24);
	}

	.round-intro-visible.variant-pop .round-intro-content {
		animation: round-pop 900ms cubic-bezier(0.2, 0.95, 0.2, 1.18) both;
	}

	.round-intro-visible.variant-slide .round-intro-content {
		animation: round-slide 900ms cubic-bezier(0.18, 0.86, 0.24, 1) both;
	}

	.round-intro-visible.variant-shimmer .round-intro-content {
		animation: round-pop 760ms cubic-bezier(0.2, 0.95, 0.2, 1.08) both;
	}

	.round-intro-visible.variant-shimmer .round-intro-content::before {
		animation: round-shimmer 1100ms 180ms ease-out both;
	}

	.round-intro-visible.variant-flip .round-intro-title {
		transform-origin: center bottom;
		animation: round-flip 900ms cubic-bezier(0.2, 0.9, 0.2, 1.15) both;
	}

	@keyframes round-pop {
		0% {
			transform: scale(0.74);
			opacity: 0;
		}

		62% {
			transform: scale(1.045);
			opacity: 1;
		}

		100% {
			transform: scale(1);
			opacity: 1;
		}
	}

	@keyframes round-slide {
		0% {
			transform: translateY(2.2rem) skewY(-2deg);
			opacity: 0;
		}

		68% {
			transform: translateY(-0.2rem) skewY(0deg);
			opacity: 1;
		}

		100% {
			transform: translateY(0);
			opacity: 1;
		}
	}

	@keyframes round-shimmer {
		0% {
			transform: translateX(-120%);
		}

		100% {
			transform: translateX(120%);
		}
	}

	@keyframes round-flip {
		0% {
			transform: rotateX(75deg) translateY(1rem);
			opacity: 0;
		}

		58% {
			transform: rotateX(-8deg) translateY(0);
			opacity: 1;
		}

		100% {
			transform: rotateX(0deg) translateY(0);
			opacity: 1;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.round-intro-overlay,
		.round-intro-content,
		.round-intro-title,
		.round-intro-content::before {
			animation: none !important;
			transition: none;
		}
	}
</style>
