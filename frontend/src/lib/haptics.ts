const DEFAULT_BUZZER_VIBRATION_MS = 30;

export function triggerBuzzerHapticPulse(durationMs = DEFAULT_BUZZER_VIBRATION_MS): boolean {
	if (
		typeof navigator === 'undefined' ||
		typeof navigator.vibrate !== 'function' ||
		durationMs <= 0
	) {
		return false;
	}

	return navigator.vibrate(durationMs);
}
