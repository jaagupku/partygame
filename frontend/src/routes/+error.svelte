<script lang="ts">
	import { messages, pageTitle } from '$lib/i18n';

	let { status, error } = $props();
</script>

<svelte:head>
	<title>{pageTitle($messages.error.pageTitle)}</title>
</svelte:head>

<h1>{$messages.error.message(status, error?.message ?? '')}</h1>
