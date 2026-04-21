<script lang="ts">
	import { getYouTubeMedia } from '$lib/media/youtube.js';
	import YouTubePlayer from '$lib/components/YouTubePlayer.svelte';

	interface VideoQuestionMediaProps {
		step: RuntimeStepState;
		stageVariant?: boolean;
		shouldPauseMedia?: boolean;
		shouldResumePausedMedia?: boolean;
	}

	let {
		step,
		stageVariant = false,
		shouldPauseMedia = false,
		shouldResumePausedMedia = false
	}: VideoQuestionMediaProps = $props();

	let videoElement = $state<HTMLVideoElement | null>(null);
	let shouldResumeMedia = $state(false);
	let lastAutoplayKey = $state('');

	const mediaKey = $derived(
		step.media?.type_ === 'video' ? `${step.id}:${step.media.src}:${step.media.loop}` : ''
	);

	const youtubeMedia = $derived.by(() => {
		if (step.media?.type_ !== 'video') {
			return null;
		}
		return getYouTubeMedia(step.media.src, {
			autoplay: true,
			controls: false,
			loop: step.media.loop,
			origin: typeof window !== 'undefined' ? window.location.origin : undefined
		});
	});

	$effect(() => {
		if (!videoElement) {
			return;
		}

		if (!shouldPauseMedia && mediaKey && mediaKey !== lastAutoplayKey) {
			lastAutoplayKey = mediaKey;
			videoElement.play().catch(() => {
				// Ignore autoplay restrictions; the video can still be started manually or resumed later.
			});
		}

		if (shouldPauseMedia) {
			if (!videoElement.paused) {
				shouldResumeMedia = true;
				videoElement.pause();
			}
			return;
		}

		if (!shouldResumePausedMedia) {
			shouldResumeMedia = false;
			return;
		}

		if (!shouldResumeMedia) {
			return;
		}

		videoElement
			.play()
			.then(() => {
				shouldResumeMedia = false;
			})
			.catch(() => {
				shouldResumeMedia = false;
			});
	});
</script>

{#if step.media?.type_ === 'video'}
	{#if youtubeMedia}
		<YouTubePlayer
			media={youtubeMedia}
			loop={step.media.loop}
			{stageVariant}
			{shouldPauseMedia}
			{shouldResumePausedMedia}
		/>
	{:else}
		<video
			bind:this={videoElement}
			class={`w-full rounded-xl ${stageVariant ? 'mx-auto block max-h-[65vh] max-w-full object-contain' : ''}`}
			autoplay
			controls
			loop={step.media.loop}
			playsinline
			src={step.media.src}
		>
			<track kind="captions" />
		</video>
	{/if}
{/if}
