<script lang="ts">
	let { timer }: { timer: RuntimeStepState['timer'] } = $props();
	let remaining = $state(0);

	$effect(() => {
		const deadline = timer.ends_at;
		const duration = timer.seconds ?? 0;
		if (deadline == null || duration <= 0) {
			remaining = 0;
			return;
		}
		let frame: number;
		const update = () => {
			remaining = Math.max(0, deadline - Date.now() / 1000);
			if (remaining > 0) frame = requestAnimationFrame(update);
		};
		update();
		return () => cancelAnimationFrame(frame);
	});

	const progress = $derived(Math.min(1, remaining / Math.max(timer.seconds ?? 0, 1)));
</script>

{#if remaining > 0}
	<div class="timer-top-track" aria-hidden="true">
		<div
			class="timer-top-bar"
			class:danger={remaining <= 5}
			class:warning={remaining > 5 && remaining <= 10}
			style:transform={`scaleX(${progress})`}
		></div>
	</div>
{/if}

<style>
	.timer-top-track {
		position: fixed;
		inset: 0 0 auto;
		z-index: 100;
		height: 3px;
		pointer-events: none;
	}

	.timer-top-bar {
		height: 100%;
		transform-origin: left;
		background: linear-gradient(to right, #f97316, #fbbf24);
		box-shadow: 0 0 8px rgb(249 115 22 / 0.55);
	}

	.timer-top-bar.warning {
		background: linear-gradient(to right, #f59e0b, #fb923c);
	}

	.timer-top-bar.danger {
		background: linear-gradient(to right, #ef4444, #fb923c);
	}
</style>
