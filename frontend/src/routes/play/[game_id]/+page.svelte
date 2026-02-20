<script lang="ts">
	import { goto } from '$app/navigation';
	import Buzzer from '$lib/components/controller/Buzzer.svelte';
	import HostPlayer from '$lib/components/controller/HostPlayer.svelte';
	import { createControllerStore } from '$lib/controller-store.js';
	import { createLocalStorageStore } from '$lib/local-storage-store.js';
	import { onMount } from 'svelte';
	import type { Writable } from 'svelte/store';

	const { data } = $props();
	const lobby = () => data.lobby;

	const player: Writable<Player | null> = createLocalStorageStore('playerData', null);
	const controller = createControllerStore(
		{ id: $player?.id || '', isHost: lobby().host_id === $player?.id, gameState: lobby().state },
		onKick
	);

	let isConnected = $state(false);
	if ($player === null) {
		goto('/play');
	}
	const websocket = new WebSocket(
		`ws://${window.location.host}/api/v1/game/${$player?.game_id}/controller/${$player?.id}`
	);

	onMount(() => {
		websocket.onmessage = (ev: MessageEvent<any>) => {
			if (ev.type === 'message') {
				controller.onMessage(ev.data);
			}
		};
		websocket.onopen = () => {
			isConnected = true;
		};
		websocket.onclose = () => {
			isConnected = false;
		};
	});

	function sendAction(msg: any) {
		websocket.send(
			JSON.stringify({
				...msg,
				player_id: $controller.id
			})
		);
	}

	function onKick() {
		localStorage.removeItem('playerData');
		websocket.close();
		goto('/');
	}

	function startGame() {
		websocket.send(
			JSON.stringify({
				type_: 'start_game'
			})
		);
	}
</script>

<h1 class="page-title">Party Controller</h1>
<p class="page-subtitle">Connection: {isConnected ? 'Live' : 'Connecting...'}</p>

{#if $controller.gameState === 'waiting_for_players'}
	<div class="card mt-8 text-center">
		<p class="text-xl font-bold">Waiting for game to start.</p>
		{#if $controller.isHost}
			<p class="mt-2 text-lg">You are the host controller.</p>
			<button type="button" class="btn btn-primary mt-4 text-3xl" onclick={() => startGame()}>
				Start Game
			</button>
		{/if}
	</div>
{:else if $controller.gameState === 'running'}
	<div class="mt-8">
		{#if $controller.isHost}
			<HostPlayer {websocket} playerId={$controller.id} players={lobby().players} />
		{:else}
			<div class="flex justify-center">
				<Buzzer {websocket} onBuzz={sendAction} />
			</div>
		{/if}
	</div>
{/if}
