<script lang="ts">
	import { onMount } from "svelte";
    import { Sound  } from "svelte-sound";
    import buzzerWav from "$lib/assets/sounds/buzzer.wav";

	export let websocket: WebSocket;
    export let players: Map<string, Player>;
    
    const buzzerSound = new Sound(buzzerWav);

    let isActive = false;
    let activePlayer: Player | undefined;

    onMount(() => {
		websocket.addEventListener('message', function (event): void {
			const data = JSON.parse(event.data);
            if (data.type_ === 'buzzer_state') {
                const event: BuzzerStateEvent = data;
                isActive = event.state === 'active';
                if (isActive) {
                    activePlayer = undefined;
                }
            } else if (data.type_ === 'buzzer_clicked') {
                const event: BuzzerClickedEvent = data;
                activePlayer = players.get(event.player_id);
                buzzerSound.play();
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
