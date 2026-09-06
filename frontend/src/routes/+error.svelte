<script lang="ts">
	import { page } from '$app/state';
	import { messages, pageTitle } from '$lib/i18n';
</script>

<svelte:head>
	<title>{pageTitle($messages.error.pageTitle)}</title>
</svelte:head>

<h1>{$messages.error.message(page.status, page.error?.message ?? '')}</h1>
