<script lang="ts">
	import { goto } from "$app/navigation";
	import Player from "$lib/components/Player.svelte";
	import { onMount } from "svelte";

    let isConnected = false;

    onMount(() => {
        const playerData = localStorage.getItem('playerData');
        if (playerData === null) {
            goto('/play');
            return;
        }
        const player: Player = JSON.parse(playerData);

        const ws = new WebSocket(`ws://${window.location.host}/api/v1/game/${player.game_id}/controller/${player.id}`);
		ws.onmessage = (ev: MessageEvent<any>) => {
			if (ev.type === 'message') {
				const messageData = JSON.parse(ev.data);
				console.log(messageData);
			}
		};
        ws.onopen = (ev: Event) => {
            isConnected = true;
        };
    });
</script>

<p>Waiting... {isConnected}</p>


