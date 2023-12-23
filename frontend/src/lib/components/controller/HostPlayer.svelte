<script lang="ts">
	import { onMount } from 'svelte';

	export let websocket: WebSocket;
	export let playerId: string;
	export let players: Player[];

	$: playerMap = new Map(players.map((e) => [e.id, e]));

	let isBuzzerActive = false;
	let activatedPlayerid: string | undefined;

	onMount(() => {
		websocket.addEventListener('message', function (e): void {
			const data = JSON.parse(e.data);
			switch (data.type_) {
				case 'buzzer_state': {
					const event: BuzzerStateEvent = data;
					isBuzzerActive = event.state === 'active';
					if (isBuzzerActive) {
						activatedPlayerid = undefined;
					}
					break;
				}
				case 'buzzer_clicked': {
					const event: BuzzerClickedEvent = data;
					activatedPlayerid = event.player_id;
					break;
				}
			}
		});
	});

	function setBuzzerState(state: 'active' | 'deactive') {
		const event: BuzzerStateEvent = {
			type_: 'buzzer_state',
			state: state
		};
		websocket.send(JSON.stringify(event));
	}

	function awardScore(score: number) {
		if (!activatedPlayerid) {
			return;
		}
		const event: UpdateScoreEvent = {
			type_: 'update_score',
			player_id: activatedPlayerid,
			add_score: score
		};
		websocket.send(JSON.stringify(event));
	}
</script>

<div class="flex flex-col">
	<div class="btn-group-vertical variant-filled">
		{#if isBuzzerActive}
			<button type="button" on:click={() => setBuzzerState('deactive')}>Turn buzzer off</button>
		{:else}
			<button type="button" on:click={() => setBuzzerState('active')}>Activate Buzzers</button>
		{/if}
	</div>
	{#if activatedPlayerid && !isBuzzerActive}
		<div>
			<span>Player "{playerMap.get(activatedPlayerid)?.name}" pressed.</span>
		</div>
		<div class="btn-group-vertical variant-filled">
			<button type="button" on:click={() => awardScore(100)}>+100</button>
			<button type="button" on:click={() => awardScore(250)}>+250</button>
			<button type="button" on:click={() => awardScore(500)}>+500</button>
			<button type="button" on:click={() => awardScore(-100)}>-100</button>
		</div>
	{/if}
</div>
