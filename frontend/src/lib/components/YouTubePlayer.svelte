<script lang="ts">
	import { onDestroy, untrack } from 'svelte';
	import type { YouTubeMedia } from '$lib/media/youtube.js';
	import { loadYouTubeIframeApi } from '$lib/media/youtube.js';

	interface YouTubePlayerProps {
		media: YouTubeMedia | null;
		loop?: boolean;
		stageVariant?: boolean;
		shouldPauseMedia?: boolean;
		shouldResumePausedMedia?: boolean;
		playbackRevision?: number;
	}

	let {
		media,
		loop = false,
		stageVariant = false,
		shouldPauseMedia = false,
		shouldResumePausedMedia = false,
		playbackRevision = 0
	}: YouTubePlayerProps = $props();

	let youtubeContainerElement = $state<HTMLDivElement | null>(null);
	let frameShellElement = $state<HTMLDivElement | null>(null);
	let youtubePlayer: YouTubePlayer | null = null;
	let youtubePlayerReady = $state(false);
	let youtubeMaskVisible = $state(true);
	let shouldResumeMedia = $state(false);
	let initializedYouTubeKey = '';
	let frameShellWidth = $state(0);
	let frameShellHeight = $state(0);
	let lastPlaybackRevision = $state(0);

	const YOUTUBE_ASPECT_RATIO = 16 / 9;

	function destroyYouTubePlayer() {
		youtubePlayerReady = false;
		youtubeMaskVisible = false;
		youtubePlayer?.destroy();
		youtubePlayer = null;
		initializedYouTubeKey = '';
	}

	const playerKey = $derived.by(() => {
		if (!media?.videoId) {
			return '';
		}
		return `${media.videoId}:${media.startSeconds}:${loop ? 'loop' : 'once'}`;
	});
	const stageFrameStyle = $derived.by(() => {
		if (!stageVariant || frameShellWidth <= 0 || frameShellHeight <= 0) {
			return '';
		}
		const width = Math.min(frameShellWidth, frameShellHeight * YOUTUBE_ASPECT_RATIO);
		const height = width / YOUTUBE_ASPECT_RATIO;
		return `width:${width}px;height:${height}px;`;
	});

	function measureFrameShell() {
		if (!frameShellElement) {
			frameShellWidth = 0;
			frameShellHeight = 0;
			return;
		}
		frameShellWidth = frameShellElement.clientWidth;
		frameShellHeight = frameShellElement.clientHeight;
	}

	$effect(() => {
		if (!stageVariant || !frameShellElement || typeof window === 'undefined') {
			return;
		}
		measureFrameShell();
		if (!window.ResizeObserver) {
			return;
		}
		const observer = new ResizeObserver(measureFrameShell);
		observer.observe(frameShellElement);
		return () => {
			observer.disconnect();
		};
	});

	$effect(() => {
		if (!shouldPauseMedia && !shouldResumePausedMedia) {
			shouldResumeMedia = false;
		}
	});

	$effect(() => {
		// Read pause/resume props before any early return so this effect stays subscribed to them.
		const pauseRequested = shouldPauseMedia;
		const resumeRequested = shouldResumePausedMedia;
		const restartRevision = playbackRevision;
		const currentPlayer = youtubePlayer;
		const playerReady = youtubePlayerReady;
		const yt = typeof window !== 'undefined' ? window.YT : undefined;
		if (!currentPlayer || !playerReady || !yt) {
			return;
		}

		if (restartRevision > lastPlaybackRevision) {
			lastPlaybackRevision = restartRevision;
			currentPlayer.seekTo(media?.startSeconds ?? 0, true);
			currentPlayer.playVideo();
			shouldResumeMedia = false;
			return;
		}

		if (pauseRequested) {
			const playerState = currentPlayer.getPlayerState();
			if (playerState !== 2 && playerState !== 0 && playerState !== 5 && playerState !== -1) {
				shouldResumeMedia = true;
			}
			currentPlayer.pauseVideo();
			return;
		}

		if (!resumeRequested || !shouldResumeMedia) {
			return;
		}

		currentPlayer.playVideo();
		shouldResumeMedia = false;
	});

	$effect(() => {
		const currentPlayerKey = playerKey;
		const currentMedia = untrack(() => media);
		if (!youtubeContainerElement || !currentPlayerKey || !currentMedia?.videoId) {
			destroyYouTubePlayer();
			return;
		}
		if (youtubePlayer && initializedYouTubeKey === currentPlayerKey) {
			return;
		}

		let cancelled = false;
		destroyYouTubePlayer();
		youtubeMaskVisible = true;
		initializedYouTubeKey = currentPlayerKey;
		lastPlaybackRevision = untrack(() => playbackRevision);

		loadYouTubeIframeApi()
			.then((YT) => {
				if (cancelled || !youtubeContainerElement) {
					return;
				}

				const playerVars: Record<string, string | number> = {
					autoplay: untrack(() => shouldPauseMedia) ? 0 : 1,
					controls: 0,
					disablekb: 1,
					fs: 0,
					iv_load_policy: 3,
					modestbranding: 1,
					playsinline: 1,
					rel: 0,
					origin: window.location.origin
				};
				if (loop) {
					playerVars.loop = 1;
					playerVars.playlist = currentMedia.videoId;
				}
				if (currentMedia.startSeconds > 0) {
					playerVars.start = currentMedia.startSeconds;
				}

				youtubePlayer = new YT.Player(youtubeContainerElement, {
					videoId: currentMedia.videoId,
					playerVars,
					events: {
						onReady: () => {
							if (cancelled || !youtubePlayer) {
								return;
							}
							youtubePlayerReady = true;
							youtubeMaskVisible = false;
							if (untrack(() => shouldPauseMedia)) {
								shouldResumeMedia = true;
								youtubePlayer.pauseVideo();
								return;
							}
							youtubePlayer.playVideo();
						},
						onStateChange: (event) => {
							if (!window.YT) {
								return;
							}
							if (
								event.data === window.YT.PlayerState.PLAYING ||
								event.data === window.YT.PlayerState.BUFFERING
							) {
								youtubeMaskVisible = false;
							}
						}
					}
				});
			})
			.catch(() => {
				youtubePlayerReady = false;
				initializedYouTubeKey = '';
			});

		return () => {
			cancelled = true;
			if (initializedYouTubeKey === currentPlayerKey) {
				destroyYouTubePlayer();
			}
		};
	});

	onDestroy(() => {
		destroyYouTubePlayer();
	});
</script>

<div
	class={`youtube-frame-shell ${stageVariant ? 'youtube-frame-shell-stage' : ''}`}
	bind:this={frameShellElement}
>
	<div class={`youtube-frame ${stageVariant ? 'youtube-frame-stage' : ''}`} style={stageFrameStyle}>
		<div bind:this={youtubeContainerElement} class="youtube-player"></div>
		{#if youtubeMaskVisible}
			<div class="youtube-mask" aria-hidden="true"></div>
		{/if}
	</div>
</div>

<style lang="postcss">
	.youtube-frame-shell {
		width: 100%;
	}

	.youtube-frame-shell-stage {
		display: grid;
		place-items: center;
		width: 100%;
		height: 100%;
		min-height: 0;
	}

	.youtube-frame {
		position: relative;
		overflow: hidden;
		border-radius: 1rem;
		background: rgb(15 23 42 / 0.08);
		aspect-ratio: 16 / 9;
	}

	.youtube-frame-stage {
		width: 100%;
		margin-inline: auto;
	}

	.youtube-player {
		width: 100%;
		height: 100%;
	}

	.youtube-player :global(iframe) {
		width: 100%;
		height: 100%;
		border: 0;
		pointer-events: none;
	}

	.youtube-mask {
		position: absolute;
		inset: 0;
		background:
			radial-gradient(circle at 50% 50%, rgb(30 41 59 / 0.12), rgb(15 23 42 / 0.88)),
			linear-gradient(180deg, rgb(15 23 42 / 0.96), rgb(15 23 42 / 0.85));
		pointer-events: none;
	}
</style>
