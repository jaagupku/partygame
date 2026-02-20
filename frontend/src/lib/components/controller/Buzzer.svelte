<script lang="ts">
	import 'iconify-icon';
	import { onMount } from 'svelte';

	interface BuzzerProps {
		websocket: WebSocket;
		onBuzz: CallableFunction;
	}

	let { websocket, onBuzz }: BuzzerProps = $props();

	let isActive = $state(false);

	onMount(() => {
		websocket.addEventListener('message', function (event): void {
			const data = JSON.parse(event.data);
			if (data.type_ === 'buzzer_state') {
				const buzzerEvent: BuzzerStateEvent = data;
				isActive = buzzerEvent.state === 'active';
			}
		});
	});

	function onclick() {
		onBuzz({
			type_: 'buzzer_clicked'
		});
	}
</script>

<div class="card flex flex-col items-center gap-4 px-6 py-8 text-center">
	<p class="label-title text-3xl">{isActive ? 'Buzz now!' : 'Wait for host activation'}</p>
	<button type="button" disabled={!isActive} class="buzzer-button" {onclick} aria-label="buzz">
		<iconify-icon icon="fluent:hand-wave-16-filled"></iconify-icon>
	</button>
</div>

<style lang="postcss">
	.buzzer-button {
		font-size: 7rem;
		width: min(68vw, 300px);
		aspect-ratio: 1 / 1;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border-radius: 9999px;
		border: 4px solid rgba(255, 255, 255, 0.86);
		color: white;
		background: linear-gradient(145deg, #fb923c, #f97316);
		box-shadow: 0 18px 40px rgba(249, 115, 22, 0.35);
		transition:
			transform 120ms ease,
			box-shadow 120ms ease,
			filter 120ms ease;
		-webkit-tap-highlight-color: rgba(255, 255, 255, 0);
		-webkit-focus-ring-color: rgba(255, 255, 255, 0);
	}

	.buzzer-button:hover:not(:disabled) {
		transform: translateY(-2px) scale(1.01);
	}

	.buzzer-button:active:not(:disabled) {
		transform: translateY(1px) scale(0.99);
		box-shadow: 0 8px 22px rgba(249, 115, 22, 0.35);
	}

	.buzzer-button:disabled {
		cursor: not-allowed;
		filter: grayscale(0.35);
		opacity: 0.55;
		box-shadow: none;
	}
</style>
