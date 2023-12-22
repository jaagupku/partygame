<script lang="ts">
	import { onMount } from 'svelte';
	import PlayerComponent from '$lib/components/Player.svelte';
	import { createGameStore } from '$lib/game-store.js';
	import Scoreboard from '$lib/components/host/Scoreboard.svelte';
	import BuzzerStatus from '$lib/components/host/BuzzerStatus.svelte';

	export let data;
	const websocket = new WebSocket(`ws://${window.location.host}/api/v1/game/${data.lobby.id}/host`);

	const game = createGameStore(data.lobby);
	$: playerMap = new Map($game.players.map((e) => [e.id, e]));

	onMount(() => {
		websocket.onmessage = (ev: MessageEvent<any>) => {
			if (ev.type === 'message') {
				game.onMessage(ev.data);
			}
		};
		websocket.onclose = (ev: CloseEvent) => {
			console.log('disconnected Please refesh');
		};
	});

	function setHost(player: Player) {
		websocket.send(
			JSON.stringify({
				type_: 'set_host',
				player_id: player.id
			})
		);
	}

	function kickPlayer(player: Player) {
		websocket.send(
			JSON.stringify({
				type_: 'kick_player',
				player_id: player.id
			})
		);
	}
</script>

{#if $game.state == 'waiting_for_players'}
	<div class="h-full grid grid-rows-[auto_1fr_auto] gap-1">
		<span class="h3">
			Join using code <span class="h1 font-bold">{$game.join_code}</span>
		</span>

		{#if $game.players.length > 0}
			<ul class="list">
				{#each $game.players as player}
					<li>
						<PlayerComponent {player} on:click={() => setHost(player)} />
						<button
							type="button"
							class="btn variant-filled-error"
							on:click={() => kickPlayer(player)}>Kick</button
						>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
{:else if $game.state == 'running'}
	<Scoreboard players={$game.players} {playerMap} />
	<BuzzerStatus {websocket} players={playerMap} />
{/if}
