import { writable } from 'svelte/store';

export const currentUser = writable<User | null>(null);
export const authLoaded = writable(false);

export async function loadCurrentUser() {
	try {
		const response = await fetch('/api/v1/auth/me');
		if (!response.ok) {
			currentUser.set(null);
			return null;
		}
		const user = (await response.json()) as User | null;
		currentUser.set(user);
		return user;
	} finally {
		authLoaded.set(true);
	}
}

export async function logout() {
	await fetch('/api/v1/auth/logout', { method: 'POST' });
	currentUser.set(null);
}
