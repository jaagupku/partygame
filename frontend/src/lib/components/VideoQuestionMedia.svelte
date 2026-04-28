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
	let lastPlaybackKey = $state('');
	let lastPlaybackRevision = $state(0);

	const mediaKey = $derived(
		step.media?.type_ === 'video' ? `${step.id}:${step.media.src}:${step.media.loop}` : ''
	);

	const youtubeMedia = $derived.by(() => {
		if (step.media?.type_ !== 'video') {
			return null;
		}
		return getYouTubeMedia(step.media.src, {
			autoplay: !shouldPauseMedia,
			controls: false,
			loop: step.media.loop,
			origin: typeof window !== 'undefined' ? window.location.origin : undefined
		});
	});

	$effect(() => {
		if (!videoElement) {
			return;
		}

		const playbackRevision =
			step.media?.type_ === 'video' ? (step.media.playback_revision ?? 0) : 0;
		if (mediaKey !== lastPlaybackKey) {
			lastPlaybackKey = mediaKey;
			lastPlaybackRevision = playbackRevision;
		}
		if (playbackRevision > lastPlaybackRevision) {
			lastPlaybackRevision = playbackRevision;
			videoElement.currentTime = 0;
			shouldResumeMedia = false;
			videoElement.play().catch(() => {
				// Ignore autoplay restrictions; the host can press play again if needed.
			});
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
			playbackRevision={step.media.playback_revision ?? 0}
		/>
	{:else}
		<video
			bind:this={videoElement}
			class={`w-full rounded-xl ${stageVariant ? 'mx-auto block max-h-[65vh] max-w-full object-contain' : ''}`}
			autoplay={!shouldPauseMedia}
			controls
			loop={step.media.loop}
			playsinline
			src={step.media.src}
		>
			<track kind="captions" />
		</video>
	{/if}
{/if}
