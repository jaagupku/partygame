<script lang="ts">
	import 'iconify-icon';

	interface PlayerComponentProps {
		player: Player;
		onclick: () => void;
	}

	let { player, onclick }: PlayerComponentProps = $props();
</script>

<button class="btn btn-ghost w-full justify-start gap-3 text-left" {onclick}>
	{#if player.status === 'connected'}
		<iconify-icon class="text-2xl text-emerald-600" icon="fluent:person-16-filled"></iconify-icon>
	{:else}
		<iconify-icon class="text-2xl text-gray-500" icon="fluent:plug-disconnected-16-filled"
		></iconify-icon>
	{/if}
	<span class="text-xl font-bold">{player.name}</span>
	{#if player.isHost}
		<span class="badge bg-sky-100 text-sky-700">Host</span>
	{/if}
</button>
