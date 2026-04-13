<script lang="ts">
	import { browser } from '$app/environment';
	import { page } from '$app/state';

	import { locale, messages, pageTitle } from '$lib/i18n';
	import '../app.css';

	let { children } = $props();
	const definitionsEditorRoute = $derived(
		page.url.pathname.startsWith('/definitions/') && page.url.pathname !== '/definitions/'
	);
	const hostGameRoute = $derived(/^\/host\/[^/]+$/.test(page.url.pathname));

	$effect(() => {
		if (!browser) {
			return;
		}

		document.documentElement.lang = $locale;
	});
</script>

<svelte:head>
	<title>{pageTitle()}</title>
</svelte:head>

<div class:app-shell-editor={definitionsEditorRoute} class="app-shell">
	<div
		class:page-panel-editor={definitionsEditorRoute}
		class:page-panel-wide={page.url.pathname.startsWith('/definitions')}
		class:page-panel-host-game={hostGameRoute}
		class="page-panel"
	>
		{@render children()}
	</div>
</div>
