import { redirect } from '@sveltejs/kit';

export const ssr = false;
export const csr = true;

function encodeDefinitionIdForPath(definitionId: string) {
	return encodeURIComponent(definitionId);
}

export async function load({ fetch, params }) {
	const routeJoinCode = params.join_code;
	const joinCode = routeJoinCode.toUpperCase();
	let res = await fetch(`/api/v1/lobby/join-code/${joinCode}`);
	let lobby: Lobby | null = null;

	if (res.ok) {
		lobby = await res.json();
	} else if (res.status === 404) {
		res = await fetch(`/api/v1/lobby/${routeJoinCode}`);
		if (res.ok) {
			const legacyLobby: Lobby = await res.json();
			throw redirect(307, `/host/${legacyLobby.join_code}`);
		}
	}

	if (!lobby) {
		throw redirect(307, '/');
	}

	if (routeJoinCode !== lobby.join_code) {
		throw redirect(307, `/host/${lobby.join_code}`);
	}

	let definitionTitle = lobby.definition_id;

	if (lobby.definition_id) {
		const definitionRes = await fetch(
			`/api/v1/definitions/${encodeDefinitionIdForPath(lobby.definition_id)}`
		);
		if (definitionRes.ok) {
			const definition: GameDefinition = await definitionRes.json();
			definitionTitle = definition.title || definition.id;
		}
	}

	return { lobby, definitionTitle };
}
