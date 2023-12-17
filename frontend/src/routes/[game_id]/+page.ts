import { error } from '@sveltejs/kit';

export async function load({ fetch, params }) {
    const res = await fetch(`/api/v1/lobby/${params.game_id}`);
    if (res.status === 404) {
        error(404, 'Game not found.')
    }
    const lobby: Lobby = await res.json();
    return { lobby };
}