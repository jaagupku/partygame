<script lang="ts">
	import { onMount } from 'svelte';

	interface HostPlayerProps {
		websocket: WebSocket;
		playerId: string;
		players: Player[];
	}

	let { websocket, playerId, players }: HostPlayerProps = $props();

	const playerMap = $derived(new Map(players.map((e) => [e.id, e])));

	let inputScore = $state(0);
	let isBuzzerActive = $state(false);
	let activatedPlayerid = $state<string | undefined>(undefined);

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

	function setBuzzerState(state: 'active' | 'deactive', disable_activator = false) {
		const event: BuzzerStateEvent = {
			type_: 'buzzer_state',
			state,
			disable_activator
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

<div class="stack-lg">
	<section class="card stack-md">
		<h2 class="label-title text-3xl">Buzzer Controls</h2>
		{#if isBuzzerActive}
			<button type="button" class="btn btn-danger" onclick={() => setBuzzerState('deactive')}>
				Turn Buzzer Off
			</button>
		{:else}
			<button type="button" class="btn btn-primary" onclick={() => setBuzzerState('active')}>
				Activate Buzzers
			</button>
			{#if activatedPlayerid}
				<button type="button" class="btn btn-accent" onclick={() => setBuzzerState('active', true)}>
					Wrong answer: disable buzzed player
				</button>
			{/if}
		{/if}
	</section>

	{#if activatedPlayerid && !isBuzzerActive}
		<section class="card stack-md">
			<p class="text-xl font-bold">
				Player <span class="text-sky-700">{playerMap.get(activatedPlayerid)?.name}</span> buzzed first.
			</p>

			<div class="grid grid-cols-2 gap-3">
				<button type="button" class="btn btn-primary" onclick={() => awardScore(10)}>+10</button>
				<button type="button" class="btn btn-danger" onclick={() => awardScore(-10)}>-10</button>
			</div>

			<div class="flex flex-col gap-3 sm:flex-row sm:items-center">
				<input
					class="input sm:max-w-40"
					type="number"
					bind:value={inputScore}
					min="-500"
					max="500"
					aria-label="Custom score"
				/>
				<button type="button" class="btn btn-ghost" onclick={() => awardScore(inputScore)}>
					Add custom amount
				</button>
			</div>
		</section>
	{/if}
</div>
