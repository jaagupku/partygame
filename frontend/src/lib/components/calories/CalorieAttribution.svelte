<script lang="ts">
	import { messages } from '$lib/i18n';
	let { download = false }: { download?: boolean } = $props();
</script>

<p class="mt-4 text-sm theme-text-muted">
	<a
		class="underline"
		href="https://world.openfoodfacts.org"
		target="_blank"
		rel="noopener noreferrer">{$messages.calorieGame.attribution}</a
	>
	·
	<a
		class="underline"
		href="https://creativecommons.org/licenses/by-sa/3.0/"
		target="_blank"
		rel="noopener noreferrer">{$messages.calorieGame.imageLicense}</a
	>
	{#if download}
		· <a class="underline" href="/api/v1/game-types/calorie_guessing/dataset" download
			>{$messages.calorieGame.dataset}</a
		>{/if}
</p>
