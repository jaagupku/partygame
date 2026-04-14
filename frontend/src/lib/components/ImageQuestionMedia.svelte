<script lang="ts">
	import { onDestroy } from 'svelte';

	interface ImageQuestionMediaProps {
		step: RuntimeStepState;
		stageVariant?: boolean;
	}

	let { step, stageVariant = false }: ImageQuestionMediaProps = $props();

	let nowMs = $state(Date.now());
	let frameHandle: number | null = null;
	let circleX = $state(0.5);
	let circleY = $state(0.5);
	let circleVelocityX = $state(0);
	let circleVelocityY = $state(0);
	let lastCircleTimestamp = $state<number | null>(null);
	let circleKey = $state('');

	function initializeCircleMotion(key: string) {
		const angle = Math.random() * Math.PI * 2;
		const speed = 0.18 + Math.random() * 0.18;
		circleX = 0.22 + Math.random() * 0.56;
		circleY = 0.22 + Math.random() * 0.56;
		circleVelocityX = Math.cos(angle) * speed;
		circleVelocityY = Math.sin(angle) * speed;
		lastCircleTimestamp = null;
		circleKey = key;
	}

	const revealState = $derived(step.media?.reveal_state ?? 'idle');
	const revealElapsedSeconds = $derived.by(() => {
		const baseElapsed = Math.max(0, step.media?.reveal_elapsed_seconds ?? 0);
		const startedAt = step.media?.reveal_started_at;
		if (revealState !== 'running' || !startedAt) {
			return baseElapsed;
		}
		return baseElapsed + Math.max(0, nowMs / 1000 - startedAt);
	});
	const revealDurationSeconds = $derived(step.media?.reveal_duration_seconds ?? 14);
	const revealProgress = $derived(
		Math.min(revealElapsedSeconds / Math.max(revealDurationSeconds, 1), 1)
	);
	const imageRevealClass = $derived(
		`${step.media?.reveal ? `reveal-${step.media.reveal}` : 'reveal-none'} reveal-state-${revealState}`
	);
	const imageRevealStyle = $derived(
		[`--reveal-duration:${revealDurationSeconds}s`, `--reveal-progress:${revealProgress}`].join(';')
	);
	const imageStyle = $derived.by(() => {
		if (!step.media || revealState === 'revealed' || step.media.reveal === 'none') {
			return '';
		}
		if (step.media.reveal === 'blur_to_clear') {
			const blur = 18 * (1 - revealProgress);
			const scale = 1 + 0.04 * (1 - revealProgress);
			return `filter: blur(${blur}px); transform: scale(${scale});`;
		}
		if (step.media.reveal === 'zoom_out') {
			const scale = 1 + 1.4 * (1 - revealProgress);
			return `transform: scale(${scale});`;
		}
		if (step.media.reveal === 'blur_circle') {
			const blur = 18 * (1 - revealProgress);
			return `filter: blur(${blur}px);`;
		}
		return '';
	});
	const circleClipPath = $derived.by(() => {
		const radius = 10 + 14 * revealProgress;
		return `circle(${radius}% at ${circleX * 100}% ${circleY * 100}%)`;
	});

	$effect(() => {
		const key = step.id && step.media?.type_ === 'image' ? `${step.id}:${step.media.src}` : '';
		if (key && key !== circleKey) {
			initializeCircleMotion(key);
		}
		if (!key) {
			circleKey = '';
			lastCircleTimestamp = null;
		}
	});

	$effect(() => {
		if (revealState !== 'running') {
			lastCircleTimestamp = null;
			if (frameHandle !== null) {
				cancelAnimationFrame(frameHandle);
				frameHandle = null;
			}
			return;
		}

		const tick = () => {
			nowMs = Date.now();
			if (step.media?.reveal === 'blur_circle') {
				const timestamp = performance.now();
				const radius = 0.1 + 0.14 * revealProgress;
				if (lastCircleTimestamp !== null) {
					const dt = Math.min((timestamp - lastCircleTimestamp) / 1000, 0.05);
					let nextX = circleX + circleVelocityX * dt;
					let nextY = circleY + circleVelocityY * dt;
					let nextVelocityX = circleVelocityX;
					let nextVelocityY = circleVelocityY;

					if (nextX <= radius) {
						nextX = radius;
						nextVelocityX = Math.abs(nextVelocityX);
					} else if (nextX >= 1 - radius) {
						nextX = 1 - radius;
						nextVelocityX = -Math.abs(nextVelocityX);
					}

					if (nextY <= radius) {
						nextY = radius;
						nextVelocityY = Math.abs(nextVelocityY);
					} else if (nextY >= 1 - radius) {
						nextY = 1 - radius;
						nextVelocityY = -Math.abs(nextVelocityY);
					}

					circleX = nextX;
					circleY = nextY;
					circleVelocityX = nextVelocityX;
					circleVelocityY = nextVelocityY;
				}
				lastCircleTimestamp = timestamp;
			}
			frameHandle = requestAnimationFrame(tick);
		};

		frameHandle = requestAnimationFrame(tick);

		return () => {
			if (frameHandle !== null) {
				cancelAnimationFrame(frameHandle);
				frameHandle = null;
			}
		};
	});

	onDestroy(() => {
		if (frameHandle !== null) {
			cancelAnimationFrame(frameHandle);
		}
	});
</script>

{#if step.media?.type_ === 'image'}
	<div
		class={`media-frame ${imageRevealClass} ${stageVariant ? 'stage-media-frame' : ''}`}
		style={imageRevealStyle}
	>
		<div class={`media-image-wrap ${stageVariant ? 'media-image-wrap-stage' : ''}`}>
			<img
				src={step.media.src}
				alt={step.title}
				class={`media-image ${stageVariant ? 'media-image-stage' : ''}`}
				style={imageStyle}
			/>
			{#if step.media.reveal === 'blur_circle' && revealState !== 'revealed'}
				<div
					class="media-spotlight"
					style={`background-image:url('${step.media.src}'); clip-path:${circleClipPath};`}
				></div>
			{/if}
		</div>
	</div>
{/if}

<style lang="postcss">
	.media-frame {
		position: relative;
		display: grid;
		place-items: center;
		overflow: hidden;
		border-radius: 1rem;
		background: rgba(15, 23, 42, 0.08);
	}

	.media-image-wrap {
		position: relative;
		display: inline-grid;
		width: 100%;
		max-width: 100%;
	}

	.media-image {
		display: block;
		grid-area: 1 / 1;
		width: 100%;
		height: auto;
		object-fit: cover;
	}

	.media-image-wrap-stage {
		justify-self: center;
		align-self: center;
		width: auto;
		height: 100%;
		max-width: 100%;
		max-height: 100%;
	}

	.media-image-stage {
		position: relative;
		width: auto;
		height: 100%;
		max-width: 100%;
		max-height: 100%;
		min-width: 0;
		min-height: 0;
		object-fit: contain;
	}

	.stage-media-frame {
		position: relative;
		min-height: 0;
		height: 100%;
		width: auto;
		max-width: 100%;
		max-height: 100%;
	}

	.reveal-blur_to_clear .media-image {
		filter: blur(18px);
	}

	.reveal-zoom_out .media-image {
		transform: scale(2.4);
		transform-origin: 58% 42%;
	}

	.reveal-blur_circle .media-image {
		filter: blur(18px);
	}

	.media-spotlight {
		position: absolute;
		inset: 0;
		grid-area: 1 / 1;
		background-position: center;
		background-repeat: no-repeat;
		background-size: contain;
		border-radius: 999px;
		clip-path: circle(8% at 20% 20%);
	}

	.reveal-none .media-image {
		filter: none;
		transform: none;
	}

	.reveal-state-revealed .media-image {
		filter: none;
		transform: none;
	}
</style>
