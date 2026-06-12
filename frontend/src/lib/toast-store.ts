import { writable } from 'svelte/store';

export type ToastTone = 'success' | 'status' | 'error';

export type ToastMessage = {
	id: string;
	message: string;
	tone: ToastTone;
};

const SUCCESS_TOAST_DURATION_MS = 5_000;

export const toasts = writable<ToastMessage[]>([]);

function createToastId() {
	return `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function dismissToast(id: string) {
	toasts.update((items) => items.filter((item) => item.id !== id));
}

export function showToast(message: string, tone: ToastTone = 'status') {
	const id = createToastId();
	toasts.update((items) => [...items, { id, message, tone }]);

	if (tone !== 'error') {
		globalThis.setTimeout(() => dismissToast(id), SUCCESS_TOAST_DURATION_MS);
	}

	return id;
}

export function showStatusToast(message: string) {
	return showToast(message, 'status');
}

export function showSuccessToast(message: string) {
	return showToast(message, 'success');
}

export function showErrorToast(message: string) {
	return showToast(message, 'error');
}
