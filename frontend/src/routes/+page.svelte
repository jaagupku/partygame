<script lang="ts">
	import { goto } from '$app/navigation';

	async function createGame() {
		const res = await fetch('/api/v1/lobby/create', {
			method: 'POST',
		});
		const lobby: Lobby = await res.json();
		goto(`/host/${lobby.id}`);
	}
</script>

<div class="container">
	<button class="btn btn-blue" on:click={createGame}> Create Game </button>
	<button class="btn btn-blue" on:click={() => goto('/play')}> Join Game </button>
</div>

<style lang="postcss">
	.btn {
		@apply font-bold h-32 w-96 rounded text-6xl m-1;
	}
	.btn-blue {
		@apply bg-primary-500 text-white;
	}
	.btn-blue:hover {
		@apply bg-primary-700;
	}
</style>
