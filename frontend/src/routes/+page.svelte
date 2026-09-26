<script lang="ts">
	import { onMount } from 'svelte';
	import { loadGameCatalog, type GameType } from '$lib/game-catalog';

	import { messages } from '$lib/i18n';
	let games = $state<GameType[]>([]);
	let loading = $state(true);
	let failed = $state(false);

	async function loadGames() {
		loading = true;
		failed = false;
		try {
			games = await loadGameCatalog();
		} catch {
			failed = true;
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		void loadGames();
	});
</script>

<svelte:head>
	<title>{$messages.common.appName}</title>
	<meta name="description" content={$messages.home.subtitle} />
	<meta property="og:title" content={$messages.common.appName} />
	<meta property="og:description" content={$messages.home.subtitle} />
	<meta property="og:site_name" content={$messages.common.appName} />
	<meta property="og:type" content="website" />
	<meta name="twitter:card" content="summary" />
	<meta name="twitter:title" content={$messages.common.appName} />
	<meta name="twitter:description" content={$messages.home.subtitle} />
</svelte:head>

<div class="md:pt-8">
	<h1 class="page-title">{$messages.common.appName}</h1>
	<p class="page-subtitle">{$messages.home.subtitle}</p>

	<div class="stack-lg">
		<a class="btn btn-accent min-h-24 text-3xl md:text-4xl" href="/play">{$messages.home.join}</a>

		<section aria-labelledby="game-selector-title" class="stack-md">
			<h2 id="game-selector-title" class="text-2xl font-bold">{$messages.gameCatalog.title}</h2>
			{#if loading}
				<p role="status">{$messages.gameCatalog.loading}</p>
			{:else if failed}
				<div class="card stack-md" role="alert">
					<p>{$messages.gameCatalog.loadFailed}</p>
					<button class="btn btn-primary" onclick={loadGames}>{$messages.gameCatalog.retry}</button>
				</div>
			{:else}
				<div class="grid gap-4 sm:grid-cols-2">
					{#each games as game (game.id)}
						{@const copy = $messages.gameCatalog[game.localization_key]}
						{@const available = game.availability === 'available'}
						<div class="card relative flex min-h-64 flex-col gap-4" class:playable-tile={available}>
							<span
								class="theme-soft-primary flex h-16 w-16 items-center justify-center rounded-2xl text-4xl"
								aria-hidden="true">{game.id === 'trivia' ? '?' : '€'}</span
							>
							<h3 class="text-2xl font-extrabold">
								{#if available}
									<a
										class="after:absolute after:inset-0 after:rounded-2xl focus-visible:outline-none focus-visible:after:outline-4 focus-visible:after:outline-offset-4"
										href={`/create?game=${encodeURIComponent(game.id)}`}>{copy.title}</a
									>
								{:else}
									<button disabled class="text-left" aria-describedby={`game-status-${game.id}`}
										>{copy.title}</button
									>
								{/if}
							</h3>
							<p class="theme-text-muted flex-1">{copy.description}</p>
							<p id={`game-status-${game.id}`} class="text-sm font-bold">
								{available ? $messages.gameCatalog.available : $messages.gameCatalog.comingSoon}
							</p>
						</div>
					{/each}
				</div>
			{/if}
		</section>
	</div>
</div>

<style>
	.playable-tile {
		transition:
			transform 180ms ease,
			box-shadow 180ms ease,
			border-color 180ms ease;
	}

	.playable-tile:focus-within {
		border-color: var(--party-primary);
		box-shadow: 0 8px 24px color-mix(in srgb, var(--party-primary), transparent 80%);
	}

	@media (hover: hover) {
		.playable-tile:hover {
			transform: translateY(-4px);
			border-color: var(--party-primary);
			box-shadow: 0 8px 24px color-mix(in srgb, var(--party-primary), transparent 80%);
		}
	}

	.playable-tile:active {
		transform: translateY(0);
	}

	@media (prefers-reduced-motion: reduce) {
		.playable-tile {
			transition: none;
		}

		.playable-tile:hover {
			transform: none;
		}
	}
</style>
