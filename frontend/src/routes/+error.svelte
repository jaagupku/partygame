<script lang="ts">
	let { status, error } = $props();
</script>

<h1>{status}: {error?.message}</h1>
