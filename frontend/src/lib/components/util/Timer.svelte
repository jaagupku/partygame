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
	const totalSeconds = $derived(h * 3600 + m * 60 + s);

	function updateTimer() {
		now = Date.now();
	}

	let interval = setInterval(updateTimer, 1000);

	const duration = 1000;
	const progress = new Tween(1, { duration, easing });

	$effect(() => {
		// Reset the countdown whenever a new duration is provided.
		countdown;
		startedAt = Date.now();
		now = startedAt;
	});

	$effect(() => {
		const safeCountdown = Math.max(countdown, 1);
		progress.set(Math.max(count - 1, 0) / safeCountdown);
	});

	function padValue(value: number, length = 2, char = '0') {
		const { length: currentLength } = value.toString();
		if (currentLength >= length) {
			return value.toString();
		}
		return `${char.repeat(length - currentLength)}${value}`;
	}

	const formattedTime = $derived(
		h > 0 ? `${padValue(h)}:${padValue(m)}:${padValue(s)}` : `${padValue(m)}:${padValue(s)}`
	);
	const progressPercent = $derived(Math.max(Math.min(progress.current * 100, 100), 0));
	const statusTone = $derived(
		totalSeconds <= 5 ? 'danger' : totalSeconds <= 10 ? 'warning' : 'default'
	);
	const toneClasses = $derived(
		statusTone === 'danger'
			? {
					panel: 'border-red-200 bg-red-50/90 text-red-950 shadow-red-100/70',
					label: 'text-red-700',
					time: 'text-red-950',
					bar: 'bg-gradient-to-r from-red-500 to-orange-400',
					pulse: 'bg-red-500'
				}
			: statusTone === 'warning'
				? {
						panel: 'border-amber-200 bg-amber-50/90 text-amber-950 shadow-amber-100/70',
						label: 'text-amber-700',
						time: 'text-amber-950',
						bar: 'bg-gradient-to-r from-amber-500 to-orange-400',
						pulse: 'bg-amber-500'
					}
				: {
						panel: 'border-sky-200 bg-white/90 text-slate-900 shadow-sky-100/80',
						label: 'text-sky-700',
						time: 'text-slate-950',
						bar: 'bg-gradient-to-r from-sky-500 to-cyan-400',
						pulse: 'bg-sky-500'
					}
	);

	onDestroy(() => {
		clearInterval(interval);
	});
</script>

<div
	in:fly={{ y: -5 }}
	class={`timer-panel w-full rounded-[1.5rem] border px-4 py-3 shadow-sm transition-colors ${toneClasses.panel}`}
	role="timer"
	aria-label={`Time remaining: ${formattedTime}`}
>
	<div class="flex items-center justify-between gap-4">
		<div class="min-w-0">
			<p class={`text-[0.7rem] font-black uppercase tracking-[0.24em] ${toneClasses.label}`}>
				Time remaining
			</p>
			<p class={`mt-1 font-black leading-none tracking-[-0.04em] ${toneClasses.time}`}>
				{formattedTime}
			</p>
		</div>
		<div class="flex items-center gap-2 text-sm font-semibold text-slate-500">
			<span class={`h-2.5 w-2.5 rounded-full ${toneClasses.pulse}`}></span>
			<span>{count}s</span>
		</div>
	</div>

	<div class="mt-3 h-2 overflow-hidden rounded-full bg-slate-200/80">
		<div
			class={`h-full rounded-full ${toneClasses.bar}`}
			style={`width: ${progressPercent}%`}
			aria-hidden="true"
		></div>
	</div>
</div>

<style>
	.timer-panel {
		backdrop-filter: blur(12px);
	}

	.timer-panel p:last-child {
		font-size: clamp(2rem, 4.5vw, 3.35rem);
	}
</style>
