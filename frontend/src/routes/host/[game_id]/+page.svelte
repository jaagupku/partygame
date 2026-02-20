<script lang="ts">
	import { onMount } from 'svelte';
	import PlayerComponent from '$lib/components/Player.svelte';
	import { createGameStore } from '$lib/game-store.js';
	import Scoreboard from '$lib/components/host/Scoreboard.svelte';
	import BuzzerStatus from '$lib/components/host/BuzzerStatus.svelte';

	const { data } = $props();
	const lobby = () => data.lobby;
	const websocket = new WebSocket(`ws://${window.location.host}/api/v1/game/${lobby().id}/host`);

	const game = createGameStore(lobby());
	const playerMap = $derived(new Map($game.players.map((e) => [e.id, e])));

	onMount(() => {
		websocket.onmessage = (ev: MessageEvent<any>) => {
			if (ev.type === 'message') {
				game.onMessage(ev.data);
			}
		};
		websocket.onclose = () => {
			console.log('disconnected Please refresh');
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
	<h1 class="page-title">Host Lobby</h1>
	<p class="page-subtitle">
		Join code: <span class="font-extrabold tracking-[0.24em]">{$game.join_code}</span>
	</p>

	{#if $game.players.length > 0}
		<ul class="stack-md mt-8">
			{#each $game.players as player}
				<li class="card flex flex-wrap items-center justify-between gap-3">
					<PlayerComponent {player} onclick={() => setHost(player)} />
					<button type="button" class="btn btn-danger" onclick={() => kickPlayer(player)}
						>Kick</button
					>
				</li>
			{/each}
		</ul>
	{/if}
{:else if $game.state == 'running'}
	<h1 class="page-title">Game Running</h1>
	<p class="page-subtitle">Live scoreboard and buzzer feed.</p>
	<div class="mt-8 stack-lg">
		<Scoreboard players={$game.players} {playerMap} />
		<BuzzerStatus {websocket} players={playerMap} />
	</div>
{/if}
