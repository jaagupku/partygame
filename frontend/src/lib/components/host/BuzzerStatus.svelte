<script lang="ts">
	import { onMount } from "svelte";

	export let websocket: WebSocket;
    export let players: Map<string, Player>;

    let isActive = false;
    let activePlayer: Player | undefined;

    onMount(() => {
		websocket.addEventListener('message', function (event): void {
			const data = JSON.parse(event.data);
            if (data.type_ === 'buzzer_state') {
                const event: BuzzerStateEvent = data;
                isActive = event.state === 'active';
            } else if (data.type_ === 'buzzer_clicked') {
                const event: BuzzerClickedEvent = data;
                activePlayer = players.get(event.player_id);
            }
		});
	});
</script>

{#if isActive}
    <h2 class="h2">Buzzer is active!</h2>
{:else}
    {#if activePlayer}
        <h2 class="h2">Activated by {activePlayer.name}</h2>
    {/if}
{/if}
