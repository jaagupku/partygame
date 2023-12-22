<script lang="ts">
	import 'iconify-icon';
	import { onMount } from 'svelte';

	export let websocket: WebSocket;
	export let onBuzz: CallableFunction;

    let isActive = false;

	console.log('render', websocket);
	onMount(() => {
		websocket.addEventListener('message', function (event): void {
			const data = JSON.parse(event.data);
            if (data.type_ === 'buzzer_state') {
                const event: BuzzerStateEvent = data;
                isActive = event.state === 'active';
            }
		});
	});

	function onClick() {
		onBuzz({
			type_: 'buzzer_clicked'
		});
	}
</script>

<button type="button" disabled={!isActive} class="btn-icon buzzer-button variant-filled" on:click={onClick}
	><iconify-icon icon="fluent:hand-wave-16-filled" /></button
>

<style lang="postcss">
	.buzzer-button {
		font-size: 8rem;
		width: 300px;
		aspect-ratio: 1 / 1;
		-webkit-tap-highlight-color: rgba(255, 255, 255, 0);
		-webkit-focus-ring-color: rgba(255, 255, 255, 0);
	}
</style>
