<script lang="ts">
	import { onMount } from 'svelte';
	import { messages } from '$lib/i18n';
	let { view }: { view: DrawingGameView } = $props();
	let now = $state(Date.now() / 1000);
	onMount(() => {
		const id = setInterval(() => (now = Date.now() / 1000), 200);
		return () => clearInterval(id);
	});
	const seconds = $derived(
		Math.max(
			0,
			Math.ceil(view.paused ? (view.remaining_seconds ?? 0) : (view.deadline ?? now) - now)
		)
	);
</script>

<p class="text-xl font-bold">{$messages.drawingMashup.timeLeft}: {seconds}s</p>
