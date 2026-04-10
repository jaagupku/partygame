<script lang="ts">
	import { browser } from '$app/environment';
	import { onDestroy, onMount } from 'svelte';
	import QuestionCard from '$lib/components/QuestionCard.svelte';
	import Scoreboard from '$lib/components/host/Scoreboard.svelte';
	import Timer from '$lib/components/util/Timer.svelte';
	import { createGameStore } from '$lib/game-store.js';
	import { createReconnectingWebSocket } from '$lib/reconnecting-websocket.js';

	const { data } = $props();
	const lobby = () => data.lobby;

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
</script>

{#if $game.state === 'waiting_for_players'}
	<h1 class="page-title">Host Lobby</h1>
	<p class="page-subtitle">
		Join code: <span class="h2 font-extrabold tracking-[0.24em]">{$game.join_code}</span>
	</p>
	<p class="page-subtitle mt-2">
		Definition: <span class="font-bold">{$game.definition_id}</span> · Host mode:
		<span class="font-bold">{$game.host_enabled ? 'On' : 'Off'}</span>
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
					<div class="text-xl font-bold">{player.name}</div>
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
	<h1 class="page-title">Big Screen View</h1>
	<p class="page-subtitle">
		Phase: <span class="font-bold">{$game.phase}</span> · Submissions: {$game.submissionCount} · Pending
		review:
		{$game.pendingReviewCount}
	</p>
	<p class="page-subtitle mt-2">Connection: {isConnected ? 'Live' : 'Reconnecting...'}</p>

	<div class="mt-8 stack-lg">
		<QuestionCard
			step={$game.activeStep}
			revealedSubmission={$game.revealedSubmission}
			title="Now Playing"
		/>

		{#if countdown > 0}
			<div class="card mx-auto max-w-64">
				<Timer {countdown} />
				<p class="text-center text-sm text-slate-600">
					{$game.activeStep?.timer.enforced ? 'Timer is enforced' : 'Timer is advisory'}
				</p>
			</div>
		{/if}

		<Scoreboard players={$game.players} {playerMap} />
	</div>
{/if}
