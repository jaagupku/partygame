<script lang="ts">
	import 'iconify-icon';

	export let player: Player;

	$: host = player.isHost ? 'is host' : '';
</script>

<button on:click>
	{#if player.status === 'connected'}
		<div class="card p-4 bg-secondary-900 w-36">
			{player.name}
			{host}
		</div>
	{:else}
		<div class="card p-4 variant-filled-surface w-36">
			<iconify-icon icon="fluent:plug-disconnected-16-filled" />
			<span class="text-secondary-400">{player.name}</span>
			{host}
		</div>
	{/if}
</button>
