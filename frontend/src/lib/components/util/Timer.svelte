<script lang="ts">
	import { onDestroy } from 'svelte';
	import { Tween } from 'svelte/motion';
	import { linear as easing } from 'svelte/easing';
	import { fly } from 'svelte/transition';

	interface TimerProps {
		countdown: number;
	}

	let { countdown }: TimerProps = $props();

	let now = $state(Date.now());
	let startedAt = $state(Date.now());
	let end = $derived(startedAt + countdown * 1000);

	const count = $derived(Math.max(Math.ceil((end - now) / 1000), 0));
	const h = $derived(Math.floor(count / 3600));
	const m = $derived(Math.floor((count - h * 3600) / 60));
	const s = $derived(count - h * 3600 - m * 60);

	function updateTimer() {
		now = Date.now();
	}

	let interval = setInterval(updateTimer, 1000);

	const duration = 1000;
	const offset = new Tween(1, { duration, easing });
	const rotation = new Tween(360, { duration, easing });

	$effect(() => {
		// Reset the countdown whenever a new duration is provided.
		countdown;
		startedAt = Date.now();
		now = startedAt;
	});

	$effect(() => {
		const safeCountdown = Math.max(countdown, 1);
		offset.set(Math.max(count - 1, 0) / safeCountdown);
		rotation.set((Math.max(count - 1, 0) / safeCountdown) * 360);
	});

	function padValue(value: number, length = 2, char = '0') {
		const { length: currentLength } = value.toString();
		if (currentLength >= length) {
			return value.toString();
		}
		return `${char.repeat(length - currentLength)}${value}`;
	}

	onDestroy(() => {
		clearInterval(interval);
	});
</script>

<main>
	<svg in:fly={{ y: -5 }} viewBox="-50 -50 100 100" width="250" height="250">
		<title>Remaining seconds: {count}</title>
		<g fill="none" stroke="currentColor" stroke-width="2">
			<circle stroke="currentColor" r="46" />
			<path
				stroke="hsl(199, 89%, 48%)"
				d="M 0 -46 a 46 46 0 0 0 0 92 46 46 0 0 0 0 -92"
				pathLength="1"
				stroke-dasharray="1"
				stroke-dashoffset={offset.current}
			/>
		</g>
		<g fill="hsl(199, 89%, 48%)" stroke="none">
			<g transform="rotate({rotation.current})">
				<g transform="translate(0 -46)">
					<circle r="4" />
				</g>
			</g>
		</g>

		<g fill="currentColor" text-anchor="middle" dominant-baseline="baseline" font-size="13">
			<text x="-3" y="6.5">
				{#each Object.entries({ h, m, s }) as [key, value], i}
					{#if countdown >= 60 ** (2 - i)}
						<tspan dx="3" font-weight="bold">{padValue(value)}</tspan><tspan dx="0.5" font-size="7"
							>{key}</tspan
						>
					{/if}
				{/each}
			</text>
		</g>
	</svg>
</main>

<style>
	main {
		padding: 0.25rem 1rem;
		color: #0f172a;
	}

	main > svg {
		width: 100%;
		height: auto;
		display: block;
		margin: 0 auto;
	}
</style>
