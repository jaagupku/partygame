<script lang="ts">
	import { goto } from '$app/navigation';

	async function createGame() {
		const res = await fetch('/api/v1/lobby/create', {
			method: 'POST'
		});
		const lobby: Lobby = await res.json();
		goto(`/host/${lobby.id}`);
	}
</script>

<h1 class="page-title">Party Quiz Arena</h1>
<p class="page-subtitle">Run a game on the big screen or jump in as a player.</p>

<div class="stack-lg">
	<button class="btn btn-primary min-h-24 text-4xl md:min-h-28 md:text-5xl" onclick={createGame}>
		Create Game
	</button>
	<button
		class="btn btn-accent min-h-24 text-4xl md:min-h-28 md:text-5xl"
		onclick={() => goto('/play')}
	>
		Join Game
	</button>
</div>
