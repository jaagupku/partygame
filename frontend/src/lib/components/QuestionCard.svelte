<script lang="ts">
	import { onDestroy } from 'svelte';

	interface QuestionCardProps {
		step?: RuntimeStepState;
		title?: string;
		revealedSubmission?: RevealedSubmission;
		revealedAnswer?: RevealedAnswer;
		displayPhase?: string;
		phaseLabel?: string;
		variant?: 'default' | 'stage';
	}

	let {
		step,
		title = 'Question',
		revealedSubmission,
		revealedAnswer,
		displayPhase = 'question_active',
		phaseLabel = 'question_active',
		variant = 'default'
	}: QuestionCardProps = $props();

	let nowMs = $state(Date.now());
	let frameHandle: number | null = null;
	let circleX = $state(0.5);
	let circleY = $state(0.5);
	let circleVelocityX = $state(0);
	let circleVelocityY = $state(0);
	let lastCircleTimestamp = $state<number | null>(null);
	let circleKey = $state('');
	let audioElement = $state<HTMLAudioElement | null>(null);
	let videoElement = $state<HTMLVideoElement | null>(null);
	let shouldResumeMedia = $state(false);
	let mediaResumeKey = $state('');

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

	$effect(() => {
		const key = step?.id && step?.media?.type_ === 'image' ? `${step.id}:${step.media.src}` : '';
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
			if (step?.media?.reveal === 'blur_circle') {
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

	const revealState = $derived(step?.media?.reveal_state ?? 'idle');
	const revealElapsedSeconds = $derived.by(() => {
		const baseElapsed = Math.max(0, step?.media?.reveal_elapsed_seconds ?? 0);
		const startedAt = step?.media?.reveal_started_at;
		if (revealState !== 'running' || !startedAt) {
			return baseElapsed;
		}
		return baseElapsed + Math.max(0, nowMs / 1000 - startedAt);
	});
	const revealDurationSeconds = $derived(step?.media?.reveal_duration_seconds ?? 14);
	const revealProgress = $derived(
		Math.min(revealElapsedSeconds / Math.max(revealDurationSeconds, 1), 1)
	);
	const imageRevealClass = $derived(
		`${step?.media?.reveal ? `reveal-${step.media.reveal}` : 'reveal-none'} reveal-state-${revealState}`
	);
	const imageRevealStyle = $derived(
		[`--reveal-duration:${revealDurationSeconds}s`, `--reveal-progress:${revealProgress}`].join(';')
	);
	const imageStyle = $derived.by(() => {
		if (!step?.media || revealState === 'revealed' || step.media.reveal === 'none') {
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
	const stageVariant = $derived(variant === 'stage');
	const showingAnswerReveal = $derived(displayPhase === 'answer_reveal');
	const shouldPauseMedia = $derived(step?.input_kind === 'buzzer' && phaseLabel === 'host_review');
	const activeMediaKey = $derived(
		step?.media ? `${step.id}:${step.media.type_}:${step.media.src}` : ''
	);

	$effect(() => {
		if (activeMediaKey !== mediaResumeKey) {
			shouldResumeMedia = false;
			mediaResumeKey = activeMediaKey;
		}
	});

	$effect(() => {
		const mediaElement = audioElement ?? videoElement;
		if (!mediaElement) {
			return;
		}

		if (shouldPauseMedia) {
			if (!mediaElement.paused) {
				shouldResumeMedia = true;
				mediaElement.pause();
			}
			return;
		}

		if (!shouldResumeMedia) {
			return;
		}

		mediaElement
			.play()
			.then(() => {
				shouldResumeMedia = false;
			})
			.catch(() => {
				// Ignore autoplay/playback restrictions and keep the media paused.
				shouldResumeMedia = false;
			});
	});

	function formatRevealValue(value: unknown): string {
		if (Array.isArray(value)) {
			return value.map((entry) => String(entry)).join(' · ');
		}
		if (value && typeof value === 'object') {
			return JSON.stringify(value);
		}
		return String(value ?? '');
	}
</script>

<section
	class={`question-card card stack-md overflow-hidden ${stageVariant ? 'question-card-stage' : ''}`}
>
	<h2 class={`label-title ${stageVariant ? 'text-4xl md:text-5xl' : 'text-3xl'}`}>{title}</h2>
	{#if step}
		<h3
			class={stageVariant
				? 'text-[clamp(2rem,4vw,4rem)] font-extrabold leading-tight'
				: 'text-3xl font-extrabold'}
		>
			{step.title}
		</h3>
		{#if step.body}
			<p
				class={stageVariant
					? 'max-w-[60rem] text-[clamp(1rem,2.2vw,2rem)] leading-relaxed'
					: 'text-xl'}
			>
				{step.body}
			</p>
		{/if}
		{#if step.media?.type_ === 'image'}
			<div
				class={`media-frame ${imageRevealClass} ${stageVariant ? 'stage-media-frame' : ''}`}
				style={imageRevealStyle}
			>
				<img src={step.media.src} alt={step.title} class="media-image" style={imageStyle} />
				{#if step.media.reveal === 'blur_circle' && revealState !== 'revealed'}
					<div
						class="media-spotlight"
						style={`background-image:url('${step.media.src}'); clip-path:${circleClipPath};`}
					></div>
				{/if}
			</div>
		{:else if step.media?.type_ === 'audio'}
			<audio bind:this={audioElement} class="w-full" controls src={step.media.src}></audio>
		{:else if step.media?.type_ === 'video'}
			<video
				bind:this={videoElement}
				class={`w-full rounded-xl ${stageVariant ? 'max-h-[65vh] object-cover' : ''}`}
				controls
				loop={step.media.loop}
				src={step.media.src}
			>
				<track kind="captions" />
			</video>
		{/if}
		{#if showingAnswerReveal && revealedAnswer}
			<div
				class={`rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 ${
					stageVariant ? 'text-xl md:text-3xl' : 'text-lg'
				}`}
			>
				<p class="text-sm font-black uppercase tracking-[0.22em] text-emerald-700">
					Correct answer
				</p>
				<p class="mt-2 font-extrabold leading-tight text-slate-950">
					{formatRevealValue(revealedAnswer.value)}
				</p>
			</div>
		{:else if !showingAnswerReveal && revealedSubmission}
			<div
				class={`rounded-2xl bg-sky-50 px-4 py-3 ${stageVariant ? 'text-xl md:text-2xl' : 'text-lg'}`}
			>
				<span class="font-bold">Revealed answer:</span>
				{String(revealedSubmission.value)}
			</div>
		{/if}
	{:else}
		<p class="text-lg text-slate-500">Waiting for next question...</p>
	{/if}
</section>

<style lang="postcss">
	.media-frame {
		position: relative;
		overflow: hidden;
		border-radius: 1rem;
		background: rgba(15, 23, 42, 0.08);
	}

	.question-card-stage {
		display: grid;
		grid-template-rows: auto auto auto minmax(0, 1fr) auto;
		height: 100%;
		min-height: 0;
		padding: 1.5rem;
	}

	.media-image {
		display: block;
		width: 100%;
		height: auto;
		object-fit: cover;
	}

	.question-card-stage .media-image {
		max-height: 100%;
		object-fit: cover;
	}

	.stage-media-frame {
		min-height: 0;
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
		background-position: center;
		background-size: cover;
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
