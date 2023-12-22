<script lang="ts">
	import { goto } from '$app/navigation';
	import Buzzer from '$lib/components/controller/Buzzer.svelte';
	import HostPlayer from '$lib/components/controller/HostPlayer.svelte';
	import { createControllerStore } from '$lib/controller-store.js';
	import { onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import { localStorageStore } from '@skeletonlabs/skeleton';

	export let data;

	const player: Writable<Player | null> = localStorageStore('playerData', null);
	const controller = createControllerStore(
		{ id: $player?.id || "", isHost: data.lobby.host_id === $player?.id, gameState: data.lobby.state },
		onKick
	);

	let isConnected = false;
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
		websocket.onopen = (ev: Event) => {
			isConnected = true;
		};
		websocket.onclose = (ev: CloseEvent) => {
			console.log('disconnected Please refesh');
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

{#if $controller.gameState === 'waiting_for_players'}
	<p>Waiting for game to start.</p>
	{#if $controller.isHost}
		<p>You are host.</p>
		<button type="button" class="btn variant-filled-primary font-bold" on:click={() => startGame()}
			>Start Game</button
		>
	{/if}
{:else if $controller.gameState === 'running'}
	{#if $controller.isHost}
		<HostPlayer {websocket} playerId={$controller.id} />
	{:else}
		<Buzzer {websocket} onBuzz={sendAction} />
	{/if}
{/if}
