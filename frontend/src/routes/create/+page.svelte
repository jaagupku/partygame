<script lang="ts">
	import { page } from '$app/state';
	import { messages } from '$lib/i18n';
	import PriceGameSetup from '$lib/components/prices/PriceGameSetup.svelte';
	import TriviaGameSetup from '$lib/components/setup/TriviaGameSetup.svelte';
</script>

{#if page.url.searchParams.get('game') === 'price_guessing'}
	<PriceGameSetup />
{:else if !page.url.searchParams.get('game') || page.url.searchParams.get('game') === 'trivia'}
	<TriviaGameSetup />
{:else}
	<p role="status">{$messages.gameCatalog.unavailable}</p>
{/if}
