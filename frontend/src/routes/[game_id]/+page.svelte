<script lang="ts">
	import { onMount } from 'svelte';
    import Player from '$lib/components/Player.svelte';

	export let data;

    onMount(() => {
        const ws = new WebSocket(`${import.meta.env.VITE_API_SOCKET_URL}/api/v1/game/${data.lobby.id}/host`);
        ws.onmessage = (ev: MessageEvent<any>) => {
            if (ev.type === 'message') {
                const messageData = JSON.parse(ev.data);
                if (messageData.type_ === 'player_joined') {
                    const event: PlayerJoinedEvent = messageData;
                    data.lobby.players = [...data.lobby.players, event.player];
                }
            }
        };
    });
</script>

<p>
	Join code {data.lobby.join_code}
</p>

{#if data.lobby.players.length > 0}
	<ul class="list">
        {#each data.lobby.players as player }
            <li><Player player={player} /></li>
        {/each}
    </ul>
{/if}
