<script lang="ts">
	import '../app.css';

	let { children } = $props();
</script>

<div class="app-shell">
	<div class="page-panel">
		{@render children()}
	</div>
</div>
