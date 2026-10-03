<script lang="ts">
	import { onMount } from 'svelte';
	import { fly } from 'svelte/transition';
	import Avatar from '$lib/components/Avatar.svelte';
	import { messages } from '$lib/i18n';
	import { waitingPlayers } from '$lib/waiting-players';

	let { gameState }: { gameState: HostGameState } = $props();
	const waiting = $derived(waitingPlayers(gameState));
	let phaseKey = $state('');
	let slots = $state<string[]>([]);
	let height = $state(0);
	let reducedMotion = $state(false);
	const pending = $derived(new Map(waiting.players.map((player) => [player.id, player])));
	$effect(() => {
		const ids = gameState.players.filter((p) => p.id !== gameState.host_id).map((p) => p.id);
		if (phaseKey !== waiting.key) {
			phaseKey = waiting.key;
			slots = ids;
		} else {
			const additions = ids.filter((id) => !slots.includes(id));
			if (additions.length) slots = [...slots, ...additions];
		}
	});
	const size = $derived(slots.length * 56 - 8 <= height ? 48 : 32);
	const rows = $derived(Math.max(1, Math.floor((height + 8) / (size + 8))));
	const columns = $derived(Math.max(1, Math.ceil(slots.length / rows)));
	const width = $derived(columns * (size + 8) + 8);

	onMount(() => {
		const media = window.matchMedia('(prefers-reduced-motion: reduce)');
		const update = () => {
			reducedMotion = media.matches;
		};
		update();
		media.addEventListener('change', update);
		return () => media.removeEventListener('change', update);
	});
</script>

<div class="waiting-rail" bind:clientHeight={height} style:width={`${width}px`}>
	{#key waiting.key}
		<div
			class="waiting-grid"
			style:grid-template-rows={`repeat(${Math.min(rows, slots.length)}, ${size}px)`}
			style:grid-auto-columns={`${size}px`}
		>
			{#each slots as id (id)}
				{@const player = pending.get(id)}
				<div class="waiting-slot" style:width={`${size}px`} style:height={`${size}px`}>
					{#if player && waiting.action}
						<div
							class="waiting-avatar"
							data-player-id={id}
							role="img"
							aria-label={$messages.gameplay.waitingActions[waiting.action](player.name)}
							transition:fly|global={{ x: -width - 64, duration: reducedMotion ? 0 : 250 }}
						>
							<div aria-hidden="true">
								<Avatar
									name={player.name}
									avatarKind={player.avatar_kind}
									avatarPresetKey={player.avatar_preset_key}
									avatarUrl={player.avatar_url}
									sizeClass="h-full w-full"
								/>
							</div>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/key}
</div>

<style>
	.waiting-rail {
		position: absolute;
		inset: 16px auto 16px 0;
		pointer-events: none;
		z-index: 10;
	}
	.waiting-grid {
		position: absolute;
		left: 8px;
		top: 50%;
		transform: translateY(-50%);
		display: grid;
		grid-auto-flow: column;
		gap: 8px;
	}
	.waiting-avatar,
	.waiting-avatar > div {
		width: 100%;
		height: 100%;
	}
</style>
