<script lang="ts">
	import { browser } from '$app/environment';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';

	import { currentUser, loadCurrentUser, logout } from '$lib/auth-store';
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

	$effect(() => {
		if (!browser) {
			return;
		}
		void loadCurrentUser();
	});

	async function handleLogout() {
		await logout();
		goto('/');
	}
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
		{#if !definitionsEditorRoute && !hostGameRoute}
			<div class="mb-4 flex flex-wrap items-center justify-end gap-3 text-sm">
				{#if $currentUser}
					<span class="font-semibold text-slate-700">{$currentUser.display_name}</span>
					<button class="btn btn-ghost px-3 py-2 text-sm" type="button" onclick={handleLogout}>
						{$messages.auth.logout}
					</button>
				{:else}
					<button
						class="btn btn-ghost px-3 py-2 text-sm"
						type="button"
						onclick={() => goto('/login')}
					>
						{$messages.auth.login}
					</button>
					<button
						class="btn btn-primary px-3 py-2 text-sm"
						type="button"
						onclick={() => goto('/signup')}
					>
						{$messages.auth.signup}
					</button>
				{/if}
			</div>
		{/if}
		{@render children()}
	</div>
</div>
