<script lang="ts">
	import { onMount } from 'svelte';
	import Timer from '$lib/components/util/Timer.svelte';

	interface BuzzerStatusProps {
		websocket: WebSocket;
		players: Map<string, Player>;
	}

	let { websocket, players }: BuzzerStatusProps = $props();

	let isActive = $state(false);
	let activePlayer: Player | undefined = $state(undefined);
	let countdown: number = $state(8);

	onMount(() => {
		websocket.addEventListener('message', function (event): void {
			const data = JSON.parse(event.data);
			if (data.type_ === 'buzzer_state') {
				const event: BuzzerStateEvent = data;
				isActive = event.active;
				if (isActive) {
					activePlayer = undefined;
				}
			} else if (data.type_ === 'buzzer_clicked') {
				const event: BuzzerClickedEvent = data;
				activePlayer = players.get(event.player_id);
			}
		});
	});
</script>

<section class="card text-center">
	{#if isActive}
		<h2 class="label-title text-4xl">Buzzer is active!</h2>
		<p class="mt-2 text-lg text-slate-600">Waiting for the fastest player...</p>
	{:else if activePlayer}
		<h2 class="label-title text-4xl">Buzzed by {activePlayer.name}</h2>
		<div class="mx-auto mt-4 w-full max-w-xl">
			<Timer {countdown} />
		</div>
	{:else}
		<h2 class="label-title text-3xl">Buzzer is idle</h2>
	{/if}
</section>
