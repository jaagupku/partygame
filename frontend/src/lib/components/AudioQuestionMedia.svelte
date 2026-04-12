<script lang="ts">
	interface AudioQuestionMediaProps {
		src: string;
		shouldPauseMedia?: boolean;
		shouldResumePausedMedia?: boolean;
	}

	let {
		src,
		shouldPauseMedia = false,
		shouldResumePausedMedia = false
	}: AudioQuestionMediaProps = $props();

	let audioElement = $state<HTMLAudioElement | null>(null);
	let shouldResumeMedia = $state(false);

	$effect(() => {
		if (!audioElement) {
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

<audio bind:this={audioElement} class="w-full" controls {src}></audio>
