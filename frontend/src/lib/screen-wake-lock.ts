/**
 * Keeps the main display awake while attached (a started game). Browsers drop the lock
 * whenever the tab is hidden, so it is requested again when the display becomes visible.
 * Unsupported or refused requests (battery saver, permissions policy) are ignored.
 */
export function screenWakeLock(_node: HTMLElement) {
	let sentinel: WakeLockSentinel | null = null;
	let requesting = false;
	let attached = true;

	async function acquire() {
		if (!attached || sentinel || requesting || document.visibilityState !== 'visible') return;
		if (!('wakeLock' in navigator)) return;
		requesting = true;
		try {
			const lock = await navigator.wakeLock.request('screen');
			if (!attached) {
				void lock.release();
				return;
			}
			sentinel = lock;
			lock.addEventListener('release', () => {
				if (sentinel === lock) sentinel = null;
			});
		} catch {
			// The display still works; it may just dim on its own schedule.
		} finally {
			requesting = false;
		}
	}

	const onVisibility = () => void acquire();
	document.addEventListener('visibilitychange', onVisibility);
	void acquire();
	return {
		destroy() {
			attached = false;
			document.removeEventListener('visibilitychange', onVisibility);
			void sentinel?.release();
			sentinel = null;
		}
	};
}
