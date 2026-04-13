<script lang="ts">
	import DefinitionEditor from '$lib/components/definition-editor/DefinitionEditor.svelte';
	import { messages } from '$lib/i18n';

	const { data } = $props();
</script>

<svelte:head>
	<title
		>{$messages.definitions.editDefinitionTitle}
		{data.params.definition_id} | {$messages.common.appName}</title
	>
</svelte:head>

<DefinitionEditor definitionId={data.params.definition_id} />
