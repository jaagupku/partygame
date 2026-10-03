/** Server elapsed time anchors a monotonic local clock; snapshots can advance it, never rewind it. */
export function createPriceTransitionClock() {
	let id = '';
	let anchor = 0;
	let elapsed = 0;
	let duration = 600;
	const read = (now: number) => Math.min(duration, elapsed + Math.max(0, now - anchor));
	return {
		read,
		sync(value: PriceTransitionState, now: number) {
			elapsed = value.id === id ? Math.max(read(now), value.elapsed_ms) : value.elapsed_ms;
			id = value.id;
			duration = value.duration_ms;
			anchor = now;
			return read(now);
		}
	};
}
