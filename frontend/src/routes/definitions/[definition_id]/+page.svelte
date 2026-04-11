<script lang="ts">
	import DefinitionEditor from '$lib/components/definition-editor/DefinitionEditor.svelte';

	const { data } = $props();
</script>

<DefinitionEditor definitionId={data.params.definition_id} />
