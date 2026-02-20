<script lang="ts">
	import { goto } from '$app/navigation';

	let joinCode = $state('');
	let name = $state('');
	let submitEnabled = $state(false);

	function uppercase(node: any) {
		const transform = () => (node.value = node.value.toUpperCase());

		node.addEventListener('input', transform, { capture: true });
		transform();
	}

	async function onSubmit(e: SubmitEvent) {
		e.preventDefault();
		const res = await fetch('/api/v1/lobby/join', {
			method: 'POST',
			body: JSON.stringify({
				player_name: name,
				join_code: joinCode
			}),
			headers: {
				'Content-Type': 'application/json'
			}
		});
		const body: ConnectedToLobby = await res.json();
		localStorage.setItem('playerData', JSON.stringify(body.player));
		goto(`/play/${body.lobby.id}`);
	}

	$effect(() => {
		if (joinCode.length > 5) {
			joinCode = joinCode.substring(0, 5);
		}
		submitEnabled = joinCode.length === 5 && name.length > 0;
	});
</script>

<h1 class="page-title">Join Game</h1>
<p class="page-subtitle">Enter your player name and 5-letter lobby code.</p>

<form onsubmit={onSubmit} class="stack-lg mx-auto mt-8 max-w-sm">
	<label class="input-wrap">
		<span class="label-title">Name</span>
		<input bind:value={name} class="input" title="Name" type="text" placeholder="Your name" />
	</label>

	<label class="input-wrap">
		<span class="label-title">Join Code</span>
		<input
			use:uppercase
			bind:value={joinCode}
			class="input text-center text-4xl tracking-[0.25em]"
			title="Join code"
			type="text"
			placeholder="ABCDE"
		/>
	</label>

	<button disabled={!submitEnabled} type="submit" class="btn btn-accent mt-2 w-full text-4xl"
		>Join</button
	>
</form>
