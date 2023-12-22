<script lang="ts">
	import { onMount } from 'svelte';

	export let websocket: WebSocket;
	export let playerId: string;
	console.log('render', websocket);
	onMount(() => {
		websocket.addEventListener('message', function (event): void {
			console.log('hostmenu', event.data, playerId);
		});
	});

	function activateBuzzers() {
		websocket.send(
			JSON.stringify({
				type_: 'buzzer_state',
				state: 'active'
			})
		);
	}
</script>

<div class="btn-group-vertical variant-filled">
	<button type="button" on:click={activateBuzzers}>Activate Buzzers</button>
</div>
