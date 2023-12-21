<script lang="ts">
	import { onMount } from 'svelte';
	import PlayerComponent from '$lib/components/Player.svelte';
	import { createGameStore } from '$lib/game-store.js';

	export let data;
	let websocket: WebSocket;

	const game = createGameStore(data.lobby);

	onMount(() => {
		const ws = new WebSocket(`ws://${window.location.host}/api/v1/game/${data.lobby.id}/host`);
		ws.onmessage = (ev: MessageEvent<any>) => {
			if (ev.type === 'message') {
				game.onMessage(ev.data);
			}
		};
		ws.onclose = (ev: CloseEvent) => {
			console.log('disconnected Please refesh');
		};
		websocket = ws;
	});

	function setHost(player: Player) {
		websocket.send(JSON.stringify({
			"type_": "set_host",
			"player_id": player.id,
		}));
	}
</script>

<span class="h3">
	Join using code <span class="h1 font-bold">{$game.join_code}</span>
</span>

{#if $game.players.length > 0}
	<ul class="list">
		{#each $game.players as player}
			<li><PlayerComponent {player} on:click={() => setHost(player)} /></li>
		{/each}
	</ul>
{/if}
