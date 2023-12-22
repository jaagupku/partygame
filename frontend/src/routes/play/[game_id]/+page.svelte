<script lang="ts">
	import { goto } from '$app/navigation';
	import { createControllerStore } from '$lib/controller-store.js';
	import { onMount } from 'svelte';

	export let data;

	const controller = createControllerStore(
		{ id: '', isHost: false, gameState: data.lobby.state },
		onKick
	);

	let isConnected = false;
	let websocket: WebSocket;

	onMount(() => {
		const playerData = localStorage.getItem('playerData');
		if (playerData === null) {
			goto('/play');
			return;
		}
		const player: Player = JSON.parse(playerData);
		controller.set({
			id: player.id,
			isHost: data.lobby.host_id === player.id,
			gameState: data.lobby.state
		});

		const ws = new WebSocket(
			`ws://${window.location.host}/api/v1/game/${player.game_id}/controller/${player.id}`
		);
		ws.onmessage = (ev: MessageEvent<any>) => {
			if (ev.type === 'message') {
				controller.onMessage(ev.data);
			}
		};
		ws.onopen = (ev: Event) => {
			isConnected = true;
		};
		ws.onclose = (ev: CloseEvent) => {
			console.log('disconnected Please refesh');
		};
		websocket = ws;
	});

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
	<p>Game is running...</p>
{/if}
