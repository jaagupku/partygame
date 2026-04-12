<script lang="ts">
	import { browser } from '$app/environment';
	import { onDestroy, onMount } from 'svelte';
	import Scoreboard from '$lib/components/host/Scoreboard.svelte';
	import StepDisplayPreview from '$lib/components/StepDisplayPreview.svelte';
	import { createGameStore } from '$lib/game-store.js';
	import { createReconnectingWebSocket } from '$lib/reconnecting-websocket.js';

	const { data } = $props();
	const lobby = () => data.lobby;
	const definitionTitle = () =>
		data.definitionTitle || data.lobby.definition_id || 'Untitled Definition';

	const game = createGameStore(lobby());
	let isConnected = $state(false);
	let socket: ReturnType<typeof createReconnectingWebSocket> | null = null;
	const playerMap = $derived(new Map($game.players.map((player) => [player.id, player])));
	const countdown = $derived.by(() => {
		const endsAt = $game.activeStep?.timer.ends_at;
		if (!endsAt) {
			return 0;
		}
		return Math.max(0, Math.ceil(endsAt - Date.now() / 1000));
	});

	onMount(() => {
		if (!browser) {
			return;
		}
		const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
		socket = createReconnectingWebSocket(
			`${protocol}://${window.location.host}/api/v1/game/${lobby().id}/host`,
			{
				onMessage: (data) => game.onMessage(data),
				onStatusChange: (connected) => {
					isConnected = connected;
				}
			}
		);
		return () => {
			socket?.close();
			socket = null;
		};
	});

	onDestroy(() => {
		socket?.close();
		socket = null;
	});

	function setHost(playerId: string) {
		socket?.send(
			JSON.stringify({
				type_: 'set_host',
				player_id: playerId
			})
		);
	}
</script>

<svelte:head>
	<title>{definitionTitle()} | Host Lobby | Party Game</title>
</svelte:head>

{#if $game.state === 'waiting_for_players'}
	<h1 class="page-title">{definitionTitle()}</h1>
	<p class="page-subtitle">
		Join code:
		<span class="mt-2 block text-5xl font-black tracking-[0.28em] text-slate-950 sm:text-6xl">
			{$game.join_code}
		</span>
	</p>
	<p class="page-subtitle mt-2">
		Host mode: <span class="font-bold">{$game.host_enabled ? 'On' : 'Off'}</span>
	</p>
	<p class="page-subtitle mt-2">
		Use the host controller to start and run the game. Connection: {isConnected
			? 'Live'
			: 'Reconnecting...'}
	</p>

	{#if $game.players.length > 0}
		<ul class="stack-md mt-8">
			{#each $game.players as player}
				<li class="card flex items-center justify-between gap-3">
					<button
						type="button"
						class="text-left text-xl font-bold text-slate-800 transition-opacity hover:opacity-75"
						onclick={() => setHost(player.id)}
					>
						{player.name}
					</button>
					<div class="flex items-center gap-2">
						{#if player.isHost}
							<span class="badge bg-sky-100 text-sky-700">Host</span>
						{/if}
						<span class="text-sm text-slate-600">{player.status}</span>
					</div>
				</li>
			{/each}
		</ul>
	{/if}
{:else}
	<div class="stack-lg">
		<StepDisplayPreview
			step={$game.activeStep}
			revealedSubmission={$game.revealedSubmission}
			title="Big Screen View"
			phaseLabel={$game.phase ?? 'question_active'}
			connectionLabel={isConnected ? 'Live' : 'Reconnecting...'}
			submissionCount={$game.submissionCount}
			pendingReviewCount={$game.pendingReviewCount}
			{countdown}
		/>

		<Scoreboard players={$game.players} {playerMap} onSelectPlayer={setHost} />
	</div>
{/if}
