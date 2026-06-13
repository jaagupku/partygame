<script lang="ts">
	import { browser } from '$app/environment';
	import { page } from '$app/state';

	import { loadCurrentUser } from '$lib/auth-store';
	import AppHeader from '$lib/components/AppHeader.svelte';
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import { locale, pageTitle } from '$lib/i18n';
	import '../app.css';

	let { children } = $props();
	const definitionsEditorRoute = $derived(
		page.url.pathname.startsWith('/definitions/') && page.url.pathname !== '/definitions/'
	);
	const hostGameRoute = $derived(/^\/host\/[^/]+$/.test(page.url.pathname));
	const playerControllerRoute = $derived(/^\/play\/[^/]+$/.test(page.url.pathname));
	const hideAppHeader = $derived(definitionsEditorRoute || hostGameRoute || playerControllerRoute);

	$effect(() => {
		if (!browser) {
			return;
		}

		document.documentElement.lang = $locale;
	});

	$effect(() => {
		if (!browser) {
			return;
		}
		void loadCurrentUser();
	});
</script>

<svelte:head>
	<title>{pageTitle()}</title>
</svelte:head>

<div
	class:app-shell-editor={definitionsEditorRoute}
	class:app-shell-host-game={hostGameRoute}
	class:app-shell-controller={playerControllerRoute}
	class="app-shell"
>
	{#if !hideAppHeader}
		<div class="app-header-shell">
			<AppHeader />
		</div>
	{/if}
	<div
		class:page-panel-editor={definitionsEditorRoute}
		class:page-panel-wide={page.url.pathname.startsWith('/definitions') && !definitionsEditorRoute}
		class:page-panel-host-game={hostGameRoute}
		class:page-panel-controller={playerControllerRoute}
		class="page-panel"
	>
		{@render children()}
	</div>
</div>

<ToastContainer />
