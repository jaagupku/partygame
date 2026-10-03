// The request must start synchronously inside the lobby-creation gesture.
let activeAttempt: { cancel: () => void } | undefined;

export function beginDisplayFullscreen(): () => void {
	if (
		typeof document === 'undefined' ||
		document.fullscreenElement ||
		!document.documentElement.requestFullscreen
	)
		return () => {};

	let cancelled = false;
	let entered = false;
	const root = document.documentElement;
	const forget = () => {
		document.removeEventListener('fullscreenchange', onChange);
		if (activeAttempt === attempt) activeAttempt = undefined;
	};
	const onChange = () => {
		if (entered && document.fullscreenElement !== root) {
			entered = false;
			forget();
		}
	};
	const exit = () => {
		if (entered && document.fullscreenElement === root) {
			entered = false;
			try {
				void document.exitFullscreen().catch(() => {});
			} catch {
				/* Best effort. */
			}
		}
		forget();
	};
	const attempt = {
		cancel() {
			cancelled = true;
			exit();
		}
	};
	activeAttempt = attempt;
	try {
		void root.requestFullscreen().then(() => {
			entered = document.fullscreenElement === root;
			if (cancelled) exit();
			else if (entered) document.addEventListener('fullscreenchange', onChange);
			else forget();
		}, forget);
	} catch {
		forget();
	}
	return attempt.cancel;
}

export function exitDisplayFullscreen() {
	activeAttempt?.cancel();
}
