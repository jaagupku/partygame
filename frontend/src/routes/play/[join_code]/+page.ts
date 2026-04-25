import { redirect } from '@sveltejs/kit';

export const ssr = false;
export const csr = true;

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
			throw redirect(307, `/play/${legacyLobby.join_code}`);
		}
	}

	if (!lobby) {
		throw redirect(307, '/');
	}

	if (routeJoinCode !== lobby.join_code) {
		throw redirect(307, `/play/${lobby.join_code}`);
	}

	return { lobby };
}
