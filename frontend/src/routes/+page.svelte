<script lang="ts">
	import { goto } from '$app/navigation';

	async function createGame() {
		const res = await fetch('/api/v1/lobby/create', {
			method: 'POST'
		});
		const lobby: Lobby = await res.json();
		goto(`/${lobby.id}`);
	}
</script>

<div class="flex h-screen">
	<div class="m-auto">
		<div class="container">
			<button class="btn btn-blue" on:click={createGame}> Create Game </button>
			<button class="btn btn-blue"> Join Game </button>
		</div>
	</div>
</div>

<style lang="postcss">
	.btn {
		@apply font-bold py-6 px-10 rounded text-6xl;
	}
	.btn-blue {
		@apply bg-primary-500 text-white;
	}
	.btn-blue:hover {
		@apply bg-primary-700;
	}
</style>
