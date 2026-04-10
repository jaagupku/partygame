<script lang="ts">
	import { browser } from '$app/environment';

	import { locale } from '$lib/i18n';
	import '../app.css';

	let { children } = $props();

	$effect(() => {
		if (!browser) {
			return;
		}

		document.documentElement.lang = $locale;
	});
</script>

<div class="app-shell">
	<div class="page-panel">
		{@render children()}
	</div>
</div>
