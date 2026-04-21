<script lang="ts">
	import { onDestroy } from 'svelte';
	import {
		DEFAULT_ZOOM_OUT_ORIGIN_X,
		DEFAULT_ZOOM_OUT_ORIGIN_Y,
		DEFAULT_ZOOM_OUT_START
	} from '$lib/media/image-reveal';

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
	let imageWrapWidth = $state(0);
	let imageWrapHeight = $state(0);

	function getImageMedia(media: RuntimeStepState['media']): RuntimeImageMediaState | null {
		return media?.type_ === 'image' ? media : null;
	}

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
	const imageMedia = $derived(getImageMedia(step.media));
	const revealElapsedSeconds = $derived.by(() => {
		const baseElapsed = Math.max(0, imageMedia?.reveal_elapsed_seconds ?? 0);
		const startedAt = imageMedia?.reveal_started_at;
		if (revealState !== 'running' || !startedAt) {
			return baseElapsed;
		}
		return baseElapsed + Math.max(0, nowMs / 1000 - startedAt);
	});
	const revealDurationSeconds = $derived(step.media?.reveal_duration_seconds ?? 14);
	const timerProgress = $derived.by(() => {
		const totalDuration = step.timer.seconds;
		if (totalDuration === undefined || totalDuration === null) {
			return null;
		}
		const remainingSeconds =
			step.timer.ends_at !== undefined && step.timer.ends_at !== null
				? Math.max(0, step.timer.ends_at - nowMs / 1000)
				: (step.timer.remaining_seconds ?? totalDuration);
		return Math.min(Math.max(1 - remainingSeconds / Math.max(totalDuration, 1), 0), 1);
	});
	const revealProgress = $derived.by(() => {
		if (revealState === 'revealed') {
			return 1;
		}
		if (timerProgress !== null) {
			return timerProgress;
		}
		return Math.min(revealElapsedSeconds / Math.max(revealDurationSeconds, 1), 1);
	});
	const imageRevealClass = $derived(
		`${step.media?.reveal ? `reveal-${step.media.reveal}` : 'reveal-none'} reveal-state-${revealState}`
	);
	const imageRevealStyle = $derived(
		[`--reveal-duration:${revealDurationSeconds}s`, `--reveal-progress:${revealProgress}`].join(';')
	);
	const circleRadiusPx = $derived.by(() => {
		const minDimension = Math.min(imageWrapWidth, imageWrapHeight);
		if (minDimension <= 0) {
			return 0;
		}
		return minDimension * (0.07 + 0.11 * revealProgress);
	});
	const imageStyle = $derived.by(() => {
		if (!imageMedia || revealState === 'revealed' || imageMedia.reveal === 'none') {
			return '';
		}
		if (imageMedia.reveal === 'blur_to_clear') {
			const blur = 18 * (1 - revealProgress);
			const scale = 1 + 0.04 * (1 - revealProgress);
			return `filter: blur(${blur}px); transform: scale(${scale});`;
		}
		if (imageMedia.reveal === 'zoom_out') {
			const startZoom = imageMedia.zoom_start ?? DEFAULT_ZOOM_OUT_START;
			const originX = (imageMedia.zoom_origin_x ?? DEFAULT_ZOOM_OUT_ORIGIN_X) * 100;
			const originY = (imageMedia.zoom_origin_y ?? DEFAULT_ZOOM_OUT_ORIGIN_Y) * 100;
			const scale = 1 + (startZoom - 1) * (1 - revealProgress);
			return `transform: scale(${scale}); transform-origin: ${originX}% ${originY}%;`;
		}
		if (imageMedia.reveal === 'blur_circle') {
			return 'filter: blur(18px);';
		}
		return '';
	});
	const circleClipPath = $derived.by(() => {
		const centerX = circleX * imageWrapWidth;
		const centerY = circleY * imageWrapHeight;
		return `circle(${circleRadiusPx}px at ${centerX}px ${centerY}px)`;
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
			if (imageMedia?.reveal === 'blur_circle') {
				const timestamp = performance.now();
				const radiusX = imageWrapWidth > 0 ? circleRadiusPx / imageWrapWidth : 0;
				const radiusY = imageWrapHeight > 0 ? circleRadiusPx / imageWrapHeight : 0;
				if (lastCircleTimestamp !== null) {
					const dt = Math.min((timestamp - lastCircleTimestamp) / 1000, 0.05);
					let nextX = circleX + circleVelocityX * dt;
					let nextY = circleY + circleVelocityY * dt;
					let nextVelocityX = circleVelocityX;
					let nextVelocityY = circleVelocityY;

					if (nextX <= radiusX) {
						nextX = radiusX;
						nextVelocityX = Math.abs(nextVelocityX);
					} else if (nextX >= 1 - radiusX) {
						nextX = 1 - radiusX;
						nextVelocityX = -Math.abs(nextVelocityX);
					}

					if (nextY <= radiusY) {
						nextY = radiusY;
						nextVelocityY = Math.abs(nextVelocityY);
					} else if (nextY >= 1 - radiusY) {
						nextY = 1 - radiusY;
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
		<div
			class={`media-image-wrap ${stageVariant ? 'media-image-wrap-stage' : ''}`}
			bind:clientWidth={imageWrapWidth}
			bind:clientHeight={imageWrapHeight}
		>
			<img
				src={step.media.src}
				alt={step.title}
				class={`media-image ${stageVariant ? 'media-image-stage' : ''}`}
				style={imageStyle}
			/>
			{#if imageMedia?.reveal === 'blur_circle' && revealState !== 'revealed'}
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
		transition: filter 1s ease-out;
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
