<script lang="ts">
	import DefinitionEditor from '$lib/components/definition-editor/DefinitionEditor.svelte';

	const { data } = $props();
</script>

<svelte:head>
	<title>Edit {data.params.definition_id} | Party Game</title>
</svelte:head>

<DefinitionEditor definitionId={data.params.definition_id} />
