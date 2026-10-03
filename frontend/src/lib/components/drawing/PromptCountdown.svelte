<script lang="ts">
	import { untrack } from 'svelte';
	import { messages } from '$lib/i18n';

	let { seconds, paused }: { seconds: number; paused: boolean } = $props();
	let previous = $state(untrack(() => seconds));
	let animate = $state(false);
	let accent = $state<'pulse' | 'slide' | ''>('');
	let accentId = $state(0);
	let slots = $state(untrack(() => Math.max(3, String(seconds).length)));
	let lastSeconds = untrack(() => seconds);
	let wasPaused = untrack(() => paused);
	let activeTicks = 0;
	let accentCount = 0;

	$effect(() => {
		const current = seconds;
		const stopped = paused;
		untrack(() => {
			previous = lastSeconds;
			animate = !stopped && !wasPaused && current === lastSeconds - 1;
			if (animate) {
				activeTicks += 1;
				if (activeTicks % 8 === 0) {
					accent = accentCount++ % 2 === 0 ? 'pulse' : 'slide';
					accentId += 1;
				}
			}
			if (stopped || wasPaused || Math.abs(current - lastSeconds) > 1) accent = '';
			slots = Math.max(slots, String(current).length);
			lastSeconds = current;
			wasPaused = stopped;
		});
	});
	const digits = $derived(String(seconds).padStart(slots, ' ').split(''));
	const oldDigits = $derived(String(previous).padStart(slots, ' ').split(''));
</script>

<div class="prompt-countdown" class:paused>
	<p class="theme-text-muted text-xl font-bold" aria-hidden="true">
		{paused ? $messages.drawingMashup.paused : $messages.drawingMashup.timeLeft}
	</p>
	<p class="sr-only" role="timer" aria-live="off">
		{paused ? `${$messages.drawingMashup.paused}. ` : ''}{$messages.drawingMashup.timeLeft}: {seconds}s
	</p>
	{#key accentId}
		<div
			class="digits"
			class:pulse={accent === 'pulse'}
			class:slide={accent === 'slide'}
			aria-hidden="true"
		>
			{#each digits as digit, index (index)}
				<span class="digit" class:empty={digit === ' '}>
					{#key seconds}
						<span class:flip-in={animate && digit !== oldDigits[index]}
							>{digit === ' ' ? '\u00a0' : digit}</span
						>
						{#if animate && digit !== oldDigits[index]}
							<span class="flip-out">{oldDigits[index] === ' ' ? '\u00a0' : oldDigits[index]}</span>
						{/if}
					{/key}
				</span>
			{/each}
		</div>
	{/key}
</div>

<style>
	.prompt-countdown {
		text-align: center;
	}
	.digits {
		display: flex;
		justify-content: center;
		font-size: clamp(6rem, min(16vw, 25dvh), 14rem);
		font-weight: 900;
		font-variant-numeric: tabular-nums;
		line-height: 1.2;
	}
	.digit {
		position: relative;
		display: inline-block;
		width: 0.65em;
		perspective: 600px;
	}
	.digit.empty {
		width: 0;
		overflow: hidden;
	}
	.digit > span {
		display: block;
		white-space: pre;
		backface-visibility: hidden;
	}
	.flip-in {
		animation: flip-in 300ms ease-out both;
	}
	.digit > .flip-out {
		position: absolute;
		inset: 0;
		animation: flip-out 300ms ease-in both;
	}
	.pulse {
		animation: pulse 450ms ease-in-out;
	}
	.slide {
		animation: slide 450ms ease-in-out;
	}
	.paused .digits,
	.paused .digit > span {
		animation: none;
	}
	.paused .flip-out {
		display: none;
	}
	@keyframes flip-in {
		from {
			transform: rotateX(90deg);
			opacity: 0;
		}
		to {
			transform: rotateX(0);
			opacity: 1;
		}
	}
	@keyframes flip-out {
		from {
			transform: rotateX(0);
			opacity: 1;
		}
		to {
			transform: rotateX(-90deg);
			opacity: 0;
		}
	}
	@keyframes pulse {
		50% {
			transform: scale(1.045);
		}
	}
	@keyframes slide {
		40% {
			transform: translateY(-0.035em);
			opacity: 0.65;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.digits,
		.digit > span {
			animation: none;
		}
		.digit > .flip-out {
			display: none;
		}
	}
</style>
