<script lang="ts">
	import DrawingGameSetup from '$lib/components/drawing/DrawingGameSetup.svelte';
	import CalorieGameSetup from '$lib/components/calories/CalorieGameSetup.svelte';
	import { messages } from '$lib/i18n';
	import { loadGameCatalog, type GameType } from '$lib/game-catalog';
	import TriviaGameSetup from './TriviaGameSetup.svelte';
	import PriceGameSetup from '$lib/components/prices/PriceGameSetup.svelte';
	const { lobbyId, onprepared }: { lobbyId: string; onprepared: () => void } = $props();
	type Setup = {
		run_id: string;
		settings: GameSetupSettings;
		settings_complete: boolean;
		definition_title?: string;
	};
	let open = $state(false);
	let choosing = $state(false);
	let loading = $state(false);
	let saving = $state(false);
	let failed = $state(false);
	let error = $state<'archiveFailed' | 'changed' | 'unavailable' | 'failed' | null>(null);
	let setup = $state<Setup | null>(null);
	let catalog = $state<GameType[]>([]);
	let selected = $state<string | null>(null);
	let formKey = $state(0);
	async function configure(switchGame: boolean) {
		open = true;
		choosing = switchGame;
		loading = true;
		failed = false;
		error = null;
		try {
			const [response, games] = await Promise.all([
				fetch(`/api/v1/lobby/${lobbyId}/setup`),
				loadGameCatalog()
			]);
			if (!response.ok) throw new Error('Setup failed');
			setup = await response.json();
			catalog = games;
			selected = switchGame ? null : setup!.settings.game_type;
			formKey += 1;
		} catch {
			failed = true;
		} finally {
			loading = false;
		}
	}
	async function prepare(settings: GameSetupSettings) {
		if (!setup || saving) return;
		saving = true;
		error = null;
		try {
			const response = await fetch(`/api/v1/lobby/${lobbyId}/continue`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ expected_run_id: setup.run_id, settings })
			});
			if (!response.ok) {
				const detail = (await response.json()).detail;
				error =
					detail === 'game_archive_failed'
						? 'archiveFailed'
						: detail === 'game_run_changed'
							? 'changed'
							: ['price_content_unavailable', 'calorie_content_unavailable'].includes(detail)
								? 'unavailable'
								: 'failed';
				if (error === 'changed') onprepared();
				return;
			}
			open = false;
			onprepared();
		} catch {
			error = 'failed';
		} finally {
			saving = false;
		}
	}
	function cancel() {
		if (!saving) {
			open = false;
			error = null;
		}
	}
</script>

<section class="card stack-md my-4" aria-label={$messages.continueGame.title}>
	{#if !open}
		<h2 class="text-2xl font-bold">{$messages.continueGame.title}</h2>
		<div class="flex flex-wrap gap-3">
			<button class="btn btn-primary" onclick={() => configure(false)}
				>{$messages.continueGame.playAgain}</button
			>
			<button class="btn btn-ghost" onclick={() => configure(true)}
				>{$messages.continueGame.chooseAnother}</button
			>
		</div>
	{:else}
		<p>{$messages.continueGame.help}</p>
		{#if loading}<p role="status">{$messages.gameCatalog.loading}</p>
		{:else if failed}
			<p role="alert">{$messages.continueGame.loadFailed}</p>
			<button class="btn btn-primary" onclick={() => configure(choosing)}
				>{$messages.gameCatalog.retry}</button
			>
		{:else if setup}
			{#if choosing}
				<label class="input-wrap">
					<span class="label-title">{$messages.gameCatalog.title}</span>
					<select
						class="input"
						bind:value={selected}
						disabled={saving}
						onchange={() => {
							formKey += 1;
							error = null;
						}}
					>
						<option value={null} disabled>{$messages.gameCatalog.title}</option>
						{#each catalog.filter((g) => g.availability === 'available') as game}
							<option value={game.id}>{$messages.gameCatalog[game.localization_key].title}</option>
						{/each}
					</select>
				</label>
			{/if}
			{#if !setup.settings_complete && selected === setup.settings.game_type}<p role="status">
					{$messages.continueGame.missingSettings}
				</p>{/if}
			{#key formKey}
				{#if selected === 'drawing_mashup'}
					<DrawingGameSetup
						initialSettings={selected === setup.settings.game_type ? setup.settings : undefined}
						onsubmit={prepare}
						oncancel={cancel}
						submitLabel={$messages.continueGame.prepare}
					/>
				{:else if selected === 'calorie_guessing'}
					<CalorieGameSetup
						initialSettings={selected === setup.settings.game_type ? setup.settings : undefined}
						onsubmit={prepare}
						oncancel={cancel}
						submitLabel={$messages.continueGame.prepare}
					/>
				{:else if selected === 'price_guessing'}
					<PriceGameSetup
						initialSettings={selected === setup.settings.game_type ? setup.settings : undefined}
						onsubmit={prepare}
						oncancel={cancel}
						submitLabel={$messages.continueGame.prepare}
					/>
				{:else if selected === 'trivia'}
					<TriviaGameSetup
						initialSettings={selected === setup.settings.game_type ? setup.settings : undefined}
						frozenTitle={setup.settings.game_type === 'trivia'
							? (setup.definition_title ?? setup.settings.definition_id)
							: undefined}
						onsubmit={prepare}
						oncancel={cancel}
						submitLabel={$messages.continueGame.prepare}
					/>
				{/if}
			{/key}
		{/if}
		{#if error}<p role="alert">{$messages.continueGame[error]}</p>{/if}
		{#if !selected || loading || failed}<button
				class="btn btn-ghost"
				disabled={saving}
				onclick={cancel}>{$messages.common.back}</button
			>{/if}
	{/if}
</section>
