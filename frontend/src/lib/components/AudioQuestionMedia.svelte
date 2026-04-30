<script lang="ts">
	interface AudioQuestionMediaProps {
		src: string;
		loop?: boolean;
		volume?: number;
		shouldPauseMedia?: boolean;
		shouldResumePausedMedia?: boolean;
		playbackRevision?: number;
	}

	let {
		src,
		loop = false,
		volume = 1,
		shouldPauseMedia = false,
		shouldResumePausedMedia = false,
		playbackRevision = 0
	}: AudioQuestionMediaProps = $props();

	let audioElement = $state<HTMLAudioElement | null>(null);
	let shouldResumeMedia = $state(false);
	let lastPlaybackRevision = $state(0);

	function normalizedVolume(value: number) {
		return Math.max(0, Math.min(1, value));
	}

	$effect(() => {
		if (!audioElement) {
			return;
		}

		audioElement.volume = normalizedVolume(volume);

		if (playbackRevision > lastPlaybackRevision) {
			lastPlaybackRevision = playbackRevision;
			audioElement.currentTime = 0;
			shouldResumeMedia = false;
			audioElement.play().catch(() => {
				// Ignore autoplay restrictions; the host can press play again if needed.
			});
			return;
		}

		if (shouldPauseMedia) {
			if (!audioElement.paused) {
				shouldResumeMedia = true;
				audioElement.pause();
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

		audioElement
			.play()
			.then(() => {
				shouldResumeMedia = false;
			})
			.catch(() => {
				shouldResumeMedia = false;
			});
	});
</script>

<audio bind:this={audioElement} class="w-full" controls {loop} {src}></audio>
