<script lang="ts">
	import DefinitionEditor from '$lib/components/definition-editor/DefinitionEditor.svelte';
	import { messages } from '$lib/i18n';
</script>

<svelte:head>
	<title>{$messages.definitions.newDefinitionTitle} | {$messages.common.appName}</title>
</svelte:head>

<DefinitionEditor />
