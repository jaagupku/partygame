<script lang="ts">
	import 'iconify-icon';
	import Avatar from '$lib/components/Avatar.svelte';
	import { messages } from '$lib/i18n';

	type ScoreboardPlayer = {
		id: string;
		name: string;
		score: number;
		status: 'connected' | 'disconnected';
		avatar_kind?: 'preset' | 'custom';
		avatar_preset_key?: string;
		avatar_url?: string;
		isHost?: boolean;
	};

	interface ScoreboardProps {
		players: ScoreboardPlayer[];
		playerMap: Map<string, ScoreboardPlayer>;
		onSelectPlayer?: (playerId: string) => void;
		variant?: 'default' | 'rail' | 'overlay';
		standings?: FinalStandingEntry[];
	}

	let {
		players,
		playerMap,
		onSelectPlayer,
		variant = 'default',
		standings
	}: ScoreboardProps = $props();

	const ordered = $derived(
		standings?.length
			? standings.map((entry) => entry.player_id)
			: players
					.filter((player) => !player.isHost)
					.toSorted((a, b) => b.score - a.score)
					.map((player) => player.id)
	);
	const railVariant = $derived(variant === 'rail');
	const overlayVariant = $derived(variant === 'overlay');
	const placeByPlayerId = $derived(
		new Map((standings ?? []).map((entry) => [entry.player_id, entry.place]))
	);
</script>

<section
	class={`card ${railVariant ? 'xl:sticky xl:top-6' : ''} ${
		overlayVariant ? 'flex h-full min-h-0 flex-col overflow-hidden' : ''
	}`}
>
	<h2 class={`label-title mb-4 ${railVariant ? 'text-2xl md:text-3xl' : 'text-3xl'}`}>
		{$messages.finale.fullScoreboard}
	</h2>
	{#if onSelectPlayer}
		<p class="mb-4 text-sm text-slate-600">Click a player name to make them the host controller.</p>
	{/if}
	<ol class={`stack-md ${overlayVariant ? 'min-h-0 flex-1 overflow-y-auto pr-1' : ''}`}>
		{#each ordered as playerId, i (i)}
			<li
				class={`grid items-center gap-2 rounded-xl bg-white/70 ${
					railVariant
						? 'grid-cols-[auto_minmax(0,1fr)_auto] p-3.5'
						: 'grid-cols-[auto_1fr_auto] p-3'
				}`}
			>
				<div class="badge bg-slate-100 text-slate-700">
					#{placeByPlayerId.get(playerId) ?? i + 1}
				</div>
				{#if onSelectPlayer}
					<button
						type="button"
						class={`flex min-w-0 items-center gap-3 text-left font-bold text-slate-800 transition-opacity hover:opacity-75 ${
							railVariant ? 'text-base md:text-lg' : 'text-lg'
						}`}
						onclick={() => onSelectPlayer(playerId)}
					>
						<Avatar
							name={playerMap.get(playerId)?.name ?? playerId}
							avatarKind={playerMap.get(playerId)?.avatar_kind}
							avatarPresetKey={playerMap.get(playerId)?.avatar_preset_key}
							avatarUrl={playerMap.get(playerId)?.avatar_url}
							sizeClass={railVariant ? 'h-10 w-10' : 'h-11 w-11'}
						/>
						{#if playerMap.get(playerId)?.status === 'disconnected'}
							<iconify-icon icon="fluent:plug-disconnected-16-filled"></iconify-icon>
						{/if}
						<span class="truncate">{playerMap.get(playerId)?.name}</span>
					</button>
				{:else}
					<div
						class={`flex min-w-0 items-center gap-3 font-bold ${
							railVariant ? 'text-base md:text-lg' : 'text-lg'
						}`}
					>
						<Avatar
							name={playerMap.get(playerId)?.name ?? playerId}
							avatarKind={playerMap.get(playerId)?.avatar_kind}
							avatarPresetKey={playerMap.get(playerId)?.avatar_preset_key}
							avatarUrl={playerMap.get(playerId)?.avatar_url}
							sizeClass={railVariant ? 'h-10 w-10' : 'h-11 w-11'}
						/>
						{#if playerMap.get(playerId)?.status === 'disconnected'}
							<iconify-icon icon="fluent:plug-disconnected-16-filled"></iconify-icon>
						{/if}
						<span class="truncate">{playerMap.get(playerId)?.name}</span>
					</div>
				{/if}
				<div
					class={`font-extrabold text-sky-700 ${railVariant ? 'text-xl md:text-2xl' : 'text-2xl'}`}
				>
					{playerMap.get(playerId)?.score}
				</div>
			</li>
		{/each}
	</ol>
</section>
