<script lang="ts">
	import { goto } from '$app/navigation';

	let joinCode = '';
	let name = '';
	let submitEnabled = false;

	function uppercase(node: any) {
		const transform = () => (node.value = node.value.toUpperCase());

		node.addEventListener('input', transform, { capture: true });

		transform();
	}

	function checkLength(code: string, name: string) {
		if (code.length > 5) {
			joinCode = joinCode.substring(0, 5);
		} else if (code.length === 5 && name.length > 0) {
			submitEnabled = true;
		} else {
			submitEnabled = false;
		}
	}

	async function onSubmit(e: any) {
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

	$: checkLength(joinCode, name);
</script>

<form on:submit|preventDefault={onSubmit}>
	<label class="label">
		<h1 class="h1">Name</h1>
		<input
			bind:value={name}
			class="input text-3xl p-5 w-60"
			title="Name"
			type="text"
			placeholder="Name.."
		/>
	</label>
	<label class="label mt-3">
		<h1 class="h1">Join Code</h1>
		<input
			use:uppercase
			bind:value={joinCode}
			class="input text-6xl p-5 w-60"
			title="Join code"
			type="text"
			placeholder="ABCDF"
		/>
	</label>
	<button disabled={!submitEnabled} type="submit" class="btn btn-blue mt-3">Join</button>
</form>

<style lang="postcss">
	.btn {
		@apply font-bold p-5 w-60 rounded text-6xl;
	}
	.btn-blue {
		@apply bg-secondary-500 text-white;
	}
	.btn-blue:hover {
		@apply bg-secondary-700;
	}
</style>
