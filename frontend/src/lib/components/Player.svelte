<script lang="ts">
    import 'iconify-icon';

    export let player: Player;
</script>

{#if player.status === 'connected'}
<div class="card p-4 bg-secondary-900">
    {player.name}
</div>
{:else}
<div class="card p-4 variant-filled-surface">
    <iconify-icon icon="fluent:plug-disconnected-16-filled" /> {player.name}
</div>
{/if}
