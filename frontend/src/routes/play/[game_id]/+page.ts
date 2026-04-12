import { redirect } from '@sveltejs/kit';

export const ssr = false;
export const csr = true;

export async function load({ fetch, params }) {
	const res = await fetch(`/api/v1/lobby/${params.game_id}`);
	if (res.status === 404) {
		throw redirect(307, '/');
	}
	const lobby: Lobby = await res.json();
	return { lobby };
}
