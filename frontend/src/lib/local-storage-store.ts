import { writable, type Writable } from 'svelte/store';

export function createLocalStorageStore<T>(key: string, initialValue: T): Writable<T> {
	const store = writable(initialValue);

	if (typeof window === 'undefined') {
		return store;
	}

	const raw = localStorage.getItem(key);
	if (raw !== null) {
		try {
			store.set(JSON.parse(raw) as T);
		} catch {
			store.set(initialValue);
		}
	}

	store.subscribe((value) => {
		localStorage.setItem(key, JSON.stringify(value));
	});

	return store;
}
