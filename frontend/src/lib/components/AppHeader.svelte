<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { currentUser, logout } from '$lib/auth-store';
	import { locale, locales, messages } from '$lib/i18n';
	import ThemeModeToggle from './ThemeModeToggle.svelte';

	type BreadcrumbItem = {
		label: string;
		href?: string;
	};

	const breadcrumbs = $derived.by<BreadcrumbItem[]>(() => {
		const pathname = page.url.pathname;
		if (pathname === '/') {
			return [];
		}
		if (pathname === '/definitions') {
			return [{ label: $messages.common.home, href: '/' }, { label: $messages.definitions.title }];
		}
		if (pathname === '/create') {
			return [{ label: $messages.common.home, href: '/' }, { label: $messages.create.title }];
		}
		if (pathname === '/play') {
			return [{ label: $messages.common.home, href: '/' }, { label: $messages.join.title }];
		}
		if (pathname === '/login') {
			return [{ label: $messages.common.home, href: '/' }, { label: $messages.auth.login }];
		}
		if (pathname === '/signup') {
			return [{ label: $messages.common.home, href: '/' }, { label: $messages.auth.signup }];
		}
		if (pathname === '/admin/stats') {
			return [{ label: $messages.common.home, href: '/' }, { label: $messages.admin.title }];
		}
		return [{ label: $messages.common.home, href: '/' }];
	});

	async function handleLogout() {
		await logout();
		goto('/');
	}
</script>

<header class="app-header">
	<div class="app-header-row">
		<div class="app-header-primary">
			<button class="app-header-control" type="button" onclick={() => goto('/definitions')}>
				{$messages.common.manageDefinitions}
			</button>

			<label class="app-header-control app-header-language">
				<span class="sr-only">{$messages.common.language}</span>
				<select bind:value={$locale} aria-label={$messages.common.language}>
					{#each locales as option}
						<option value={option.code}>{option.label}</option>
					{/each}
				</select>
				<span aria-hidden="true">⌄</span>
			</label>
		</div>

		<div class="app-header-actions">
			<ThemeModeToggle />
			{#if $currentUser}
				<span class="app-header-user">{$currentUser.display_name}</span>
				{#if $currentUser.role === 'admin'}
					<button
						class="btn btn-ghost px-3 py-2 text-sm"
						type="button"
						onclick={() => goto('/admin/stats')}
					>
						{$messages.common.adminStats}
					</button>
				{/if}
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
	</div>

	{#if breadcrumbs.length > 0}
		<nav class="app-header-breadcrumb" aria-label={$messages.common.breadcrumb}>
			{#each breadcrumbs as item, index}
				{#if index > 0}
					<span aria-hidden="true">/</span>
				{/if}
				{#if item.href}
					<button type="button" onclick={() => item.href && goto(item.href)}>{item.label}</button>
				{:else}
					<span aria-current="page">{item.label}</span>
				{/if}
			{/each}
		</nav>
	{/if}
</header>

<style>
	.app-header {
		display: grid;
		gap: 0.45rem;
		width: 100%;
	}

	.app-header-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
		min-width: 0;
	}

	.app-header-primary,
	.app-header-actions {
		display: flex;
		flex-wrap: nowrap;
		align-items: center;
		gap: 0.5rem;
		min-width: 0;
	}

	.app-header-actions {
		flex: 0 1 auto;
		justify-content: flex-end;
	}

	.app-header-primary {
		flex: 0 1 auto;
	}

	.app-header-actions :global(.theme-mode-toggle) {
		box-shadow: 0 8px 18px rgb(15 23 42 / 0.07);
	}

	.app-header-actions :global(.theme-mode-toggle button) {
		width: 1.75rem;
		height: 1.75rem;
	}

	.app-header-control {
		display: inline-flex;
		flex: 0 0 auto;
		min-height: 2.35rem;
		align-items: center;
		gap: 0.6rem;
		border: 1px solid var(--party-border);
		border-radius: 999px;
		background: var(--party-surface-strong);
		padding: 0.42rem 0.85rem;
		color: var(--party-ink);
		font-size: 0.875rem;
		font-weight: 800;
		box-shadow: 0 8px 18px rgb(15 23 42 / 0.07);
		transition:
			transform 150ms ease,
			opacity 150ms ease;
	}

	.app-header-control:hover {
		opacity: 0.88;
		transform: translateY(-1px);
	}

	.app-header-language select {
		appearance: none;
		border: 0;
		background: transparent;
		color: inherit;
		font: inherit;
		outline: none;
	}

	.app-header-language select option {
		background: var(--party-surface-strong);
		color: var(--party-ink);
	}

	.app-header-user {
		min-width: 0;
		max-width: 12rem;
		overflow: hidden;
		color: var(--party-ink);
		font-weight: 800;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.app-header-breadcrumb {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem;
		color: var(--party-subtle);
		font-size: 0.85rem;
		font-weight: 700;
	}

	.app-header-breadcrumb button {
		color: inherit;
		transition: color 150ms ease;
	}

	.app-header-breadcrumb button:hover,
	.app-header-breadcrumb [aria-current='page'] {
		color: var(--party-ink);
	}

	@media (max-width: 720px) {
		.app-header-row {
			gap: 0.55rem;
		}

		.app-header-primary,
		.app-header-actions {
			gap: 0.35rem;
		}

		.app-header-control,
		.app-header-actions :global(.btn) {
			min-height: 2.15rem;
			padding: 0.34rem 0.65rem;
			font-size: 0.8rem;
		}

		.app-header-user {
			max-width: 8rem;
			font-size: 0.85rem;
		}

		.app-header-actions :global(.theme-mode-toggle button) {
			width: 1.55rem;
			height: 1.55rem;
		}
	}

	@media (max-width: 560px) {
		.app-header-row {
			align-items: flex-start;
			flex-direction: column;
		}

		.app-header-primary,
		.app-header-actions {
			flex-wrap: wrap;
		}

		.app-header-actions {
			justify-content: flex-start;
		}
	}
</style>
