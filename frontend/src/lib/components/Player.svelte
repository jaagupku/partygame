<script lang="ts">
	import 'iconify-icon';
	import Avatar from '$lib/components/Avatar.svelte';

	interface PlayerComponentProps {
		player: Player;
		onclick: () => void;
	}

	let { player, onclick }: PlayerComponentProps = $props();
</script>

<button class="btn btn-ghost w-full justify-start gap-3 text-left" {onclick}>
	<Avatar
		name={player.name}
		avatarKind={player.avatar_kind}
		avatarPresetKey={player.avatar_preset_key}
		avatarUrl={player.avatar_url}
		sizeClass="h-11 w-11"
	/>
	<span class="text-xl font-bold">{player.name}</span>
	{#if player.isHost}
		<span class="badge bg-sky-100 text-sky-700">Host</span>
	{/if}
	{#if player.status !== 'connected'}
		<iconify-icon class="ml-auto text-2xl text-gray-500" icon="fluent:plug-disconnected-16-filled"
		></iconify-icon>
	{/if}
</button>
