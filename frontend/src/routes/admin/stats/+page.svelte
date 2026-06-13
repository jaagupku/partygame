<script lang="ts">
	import { goto } from '$app/navigation';
	import { authLoaded, currentUser } from '$lib/auth-store';
	import { messages } from '$lib/i18n';
	import { showErrorToast } from '$lib/toast-store';
	import { onMount } from 'svelte';

	let loading = $state(false);
	let loadFailed = $state(false);
	let stats = $state<GameStatSummary[]>([]);
	let selectedGameId = $state<string | null>(null);
	let definitionFilter = $state('');
	let hostModeFilter = $state('');
	let finishedFromFilter = $state('');
	let finishedToFilter = $state('');

	const selectedStats = $derived(stats.find((item) => item.game_id === selectedGameId) ?? stats[0]);

	onMount(loadStats);

	async function loadStats() {
		loading = true;
		loadFailed = false;
		const params = new URLSearchParams({ limit: '100' });
		if (definitionFilter.trim()) {
			params.set('definition_id', definitionFilter.trim());
		}
		if (hostModeFilter) {
			params.set('host_enabled', hostModeFilter);
		}
		if (finishedFromFilter) {
			params.set('finished_from', finishedFromFilter);
		}
		if (finishedToFilter) {
			params.set('finished_to', finishedToFilter);
		}
		const response = await fetch(`/api/v1/admin/game-stats?${params.toString()}`);
		loading = false;
		if (response.status === 401 || response.status === 403) {
			loadFailed = true;
			stats = [];
			selectedGameId = null;
			showErrorToast($messages.admin.accessDenied);
			return;
		}
		if (!response.ok) {
			loadFailed = true;
			stats = [];
			selectedGameId = null;
			showErrorToast($messages.admin.couldNotLoadStats);
			return;
		}
		const payload = (await response.json()) as GameStatSummaryList;
		stats = payload.items;
		selectedGameId = stats[0]?.game_id ?? null;
	}

	function clearFilters() {
		definitionFilter = '';
		hostModeFilter = '';
		finishedFromFilter = '';
		finishedToFilter = '';
		void loadStats();
	}

	function formatDate(value?: string | null) {
		if (!value) {
			return '-';
		}
		return new Intl.DateTimeFormat(undefined, {
			dateStyle: 'medium',
			timeStyle: 'short'
		}).format(new Date(value));
	}

	function formatSeconds(value?: number | null) {
		if (value === undefined || value === null) {
			return '-';
		}
		return `${value.toFixed(3)}s`;
	}
</script>

<svelte:head>
	<title>{$messages.admin.title} | {$messages.common.appName}</title>
</svelte:head>

{#if $authLoaded && $currentUser?.role !== 'admin'}
	<section class="card stack-md">
		<h1 class="label-title text-3xl">{$messages.admin.accessDenied}</h1>
		<button class="btn btn-primary w-fit" type="button" onclick={() => goto('/')}>
			{$messages.common.home}
		</button>
	</section>
{:else}
	<div class="flex flex-wrap items-start justify-between gap-4">
		<div>
			<h1 class="page-title text-left">{$messages.admin.title}</h1>
			<p class="page-subtitle text-left">{$messages.admin.subtitle}</p>
		</div>
	</div>

	<div class="stack-lg">
		<section class="card stack-md">
			<div class="flex flex-wrap items-end gap-3">
				<label class="input-wrap min-w-56 flex-1">
					<span class="theme-text-muted text-sm font-bold">{$messages.admin.definition}</span>
					<input class="input text-base" bind:value={definitionFilter} placeholder="quiz_demo" />
				</label>
				<label class="input-wrap min-w-52">
					<span class="theme-text-muted text-sm font-bold">{$messages.admin.hostMode}</span>
					<div class="select-shell">
						<select class="input select-input text-base" bind:value={hostModeFilter}>
							<option value="">{$messages.admin.allHostModes}</option>
							<option value="true">{$messages.admin.hostEnabled}</option>
							<option value="false">{$messages.admin.hostless}</option>
						</select>
						<span class="select-chevron" aria-hidden="true">⌄</span>
					</div>
				</label>
				<label class="input-wrap min-w-44">
					<span class="theme-text-muted text-sm font-bold">{$messages.admin.finishedFrom}</span>
					<input class="input text-base" type="date" bind:value={finishedFromFilter} />
				</label>
				<label class="input-wrap min-w-44">
					<span class="theme-text-muted text-sm font-bold">{$messages.admin.finishedTo}</span>
					<input class="input text-base" type="date" bind:value={finishedToFilter} />
				</label>
				<button class="btn btn-primary" type="button" onclick={loadStats}>
					{$messages.admin.filter}
				</button>
				<button class="btn btn-ghost" type="button" onclick={clearFilters}>
					{$messages.admin.clear}
				</button>
			</div>
		</section>

		<section class="card stack-md">
			<div class="flex items-center justify-between gap-3">
				<h2 class="label-title text-2xl">{$messages.admin.completedGames}</h2>
				{#if loading}
					<span class="theme-text-muted text-sm">{$messages.common.loading}</span>
				{/if}
			</div>

			{#if stats.length === 0 && !loading && !loadFailed}
				<div
					class="theme-surface-muted rounded-2xl border border-dashed px-4 py-6 text-center font-semibold"
				>
					{$messages.admin.noStatsYet}
				</div>
			{:else if !loadFailed}
				<div class="overflow-x-auto">
					<table class="w-full min-w-[760px] border-separate border-spacing-y-2 text-left text-sm">
						<thead class="theme-text-muted text-xs uppercase tracking-wide">
							<tr>
								<th class="px-3 py-2">{$messages.admin.game}</th>
								<th class="px-3 py-2">{$messages.admin.definition}</th>
								<th class="px-3 py-2">{$messages.admin.finished}</th>
								<th class="px-3 py-2">{$messages.admin.players}</th>
								<th class="px-3 py-2">{$messages.admin.steps}</th>
								<th class="px-3 py-2">{$messages.admin.hostMode}</th>
							</tr>
						</thead>
						<tbody>
							{#each stats as item}
								<tr
									class={`admin-stats-row cursor-pointer rounded-2xl shadow-sm ${selectedStats?.game_id === item.game_id ? 'admin-stats-row-selected' : ''}`}
									onclick={() => (selectedGameId = item.game_id)}
								>
									<td class="rounded-l-2xl px-3 py-3 font-bold">{item.join_code}</td>
									<td class="px-3 py-3">
										{item.definition_title ?? item.definition_id ?? '-'}
									</td>
									<td class="px-3 py-3">{formatDate(item.finished_at)}</td>
									<td class="px-3 py-3">{item.player_count}</td>
									<td class="px-3 py-3">{item.step_count}</td>
									<td class="rounded-r-2xl px-3 py-3">
										{item.host_enabled ? $messages.admin.hostEnabled : $messages.admin.hostless}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</section>

		{#if selectedStats}
			<section class="grid gap-4 lg:grid-cols-2">
				<div class="card stack-md">
					<h2 class="label-title text-2xl">{$messages.admin.scoreboard}</h2>
					{#each selectedStats.summary.scoreboard ?? [] as player}
						<div
							class="theme-surface-muted flex items-center justify-between gap-3 rounded-2xl border px-4 py-3"
						>
							<span class="font-bold">{player.place}. {player.name}</span>
							<span>{player.score}</span>
						</div>
					{/each}
				</div>

				<div class="card stack-md">
					<h2 class="label-title text-2xl">{$messages.admin.answers}</h2>
					<div class="grid gap-3 sm:grid-cols-2">
						<div>
							{$messages.admin.totalSubmissions}: {selectedStats.summary.answers?.submitted_count ??
								0}
						</div>
						<div>
							{$messages.admin.reviewed}: {selectedStats.summary.answers?.reviewed_count ?? 0}
						</div>
						<div>
							{$messages.admin.correctWrong}: {selectedStats.summary.answers?.correct_count ?? 0} /
							{selectedStats.summary.answers?.wrong_count ?? 0}
						</div>
						<div>
							{$messages.admin.averageAccuracy}: {selectedStats.summary.answers
								?.average_accuracy_percent ?? '-'}%
						</div>
					</div>
				</div>

				<div class="card stack-md">
					<h2 class="label-title text-2xl">{$messages.admin.buzzers}</h2>
					<div class="grid gap-3 sm:grid-cols-2">
						<div>{$messages.admin.buzzCount}: {selectedStats.summary.buzzers?.buzz_count ?? 0}</div>
						<div>
							{$messages.admin.fastestBuzz}: {formatSeconds(
								selectedStats.summary.buzzers?.fastest_reaction_seconds
							)}
						</div>
						<div>
							{$messages.admin.medianBuzz}: {formatSeconds(
								selectedStats.summary.buzzers?.median_reaction_seconds
							)}
						</div>
						<div>
							{$messages.admin.closeCalls}: {selectedStats.summary.buzzers?.close_call_count ?? 0}
						</div>
					</div>
				</div>

				<div class="card stack-md">
					<h2 class="label-title text-2xl">{$messages.admin.reactions}</h2>
					<div class="grid gap-3 sm:grid-cols-2">
						<div>
							{$messages.admin.totalReactions}: {selectedStats.summary.reactions?.total_reactions ??
								0}
						</div>
						<div>
							{$messages.admin.mostUsedReaction}: {selectedStats.summary.reactions
								?.most_used_reaction ?? '-'}
						</div>
					</div>
					<div class="flex flex-wrap gap-2">
						{#each Object.entries(selectedStats.summary.reactions?.reaction_counts ?? {}) as [reaction, count]}
							<span class="theme-surface-muted badge border">{reaction} {count}</span>
						{/each}
					</div>
				</div>
			</section>
		{/if}
	</div>
{/if}

<style>
	.admin-stats-row {
		background: var(--party-soft-surface);
		color: var(--party-ink);
	}

	.admin-stats-row-selected {
		outline: 2px solid var(--party-primary);
		background: var(--party-soft-primary-bg);
	}
</style>
