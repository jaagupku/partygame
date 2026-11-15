<script lang="ts">
	import { goto } from '$app/navigation';
	import { messages } from '#lib/i18n.js';

	goto('/');
</script>

<svelte:head>
	<title>{$messages.hostView.hostLobbyTitle} | {$messages.common.appName}</title>
</svelte:head>
