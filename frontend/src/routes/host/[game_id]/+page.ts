import { error } from '@sveltejs/kit';

export const ssr = false;
export const csr = true;

export async function load({ fetch, params }) {
	const res = await fetch(`/api/v1/lobby/${params.game_id}`);
	if (res.status === 404) {
		error(404, 'Game not found.');
	}

	const lobby: Lobby = await res.json();
	let definitionTitle = lobby.definition_id;

	if (lobby.definition_id) {
		const definitionRes = await fetch(`/api/v1/definitions/${lobby.definition_id}`);
		if (definitionRes.ok) {
			const definition: GameDefinition = await definitionRes.json();
			definitionTitle = definition.title || definition.id;
		}
	}

	return { lobby, definitionTitle };
}
