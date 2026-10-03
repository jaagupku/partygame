export interface AudioVoice {
	volume(value: number, fadeSeconds?: number): void;
	stop(fadeSeconds?: number): void;
}
export interface AudioDriver {
	activate(): Promise<boolean>;
	play(src: string, loop: boolean, onEnd: () => void, onError: () => void): AudioVoice;
	dispose(): void;
}
let primedContext: AudioContext | undefined;
function newContext() {
	return new AudioContext();
}
/** Call synchronously inside Create, before awaiting the request. No assets or sound are played. */
export function primePresentationAudio() {
	try {
		primedContext ??= newContext();
		const context = primedContext;
		void context.resume().catch(() => {});
		return () => {
			if (primedContext === context) {
				primedContext = undefined;
				void context.close().catch(() => {});
			}
		};
	} catch {
		return () => {};
	}
}
export function createBrowserAudioDriver(): AudioDriver {
	let context: AudioContext | undefined;
	let disposed = false;
	const abort = new AbortController();
	const buffers = new Map<string, Promise<AudioBuffer>>();
	const voices = new Set<() => void>();
	function acquire() {
		if (!context) {
			context = primedContext ?? newContext();
			primedContext = undefined;
		}
		return context;
	}
	return {
		async activate() {
			if (disposed) return false;
			try {
				const ctx = acquire();
				await ctx.resume();
				return !disposed && ctx.state === 'running';
			} catch {
				return false;
			}
		},
		play(src, loop, onEnd, onError) {
			const ctx = acquire();
			const gain = ctx.createGain();
			gain.gain.value = 0;
			gain.connect(ctx.destination);
			let source: AudioBufferSourceNode | undefined;
			let stopped = false;
			let stopping = false;
			let timer: ReturnType<typeof setTimeout> | undefined;
			function finish() {
				if (stopped) return;
				stopped = true;
				clearTimeout(timer);
				if (source) {
					source.onended = null;
					source.stop();
					source.disconnect();
				}
				gain.disconnect();
				voices.delete(finish);
				onEnd();
			}
			voices.add(finish);
			let buffer = buffers.get(src);
			if (!buffer) {
				buffer = fetch(src, { signal: abort.signal })
					.then((r) => {
						if (!r.ok) throw new Error('Audio unavailable');
						return r.arrayBuffer();
					})
					.then((bytes) => ctx.decodeAudioData(bytes));
				buffers.set(src, buffer);
			}
			void buffer
				.then((decoded) => {
					if (disposed || stopped || stopping) return;
					source = ctx.createBufferSource();
					source.buffer = decoded;
					source.loop = loop;
					source.connect(gain);
					source.onended = finish;
					source.start();
				})
				.catch(() => {
					buffers.delete(src);
					if (!disposed && !stopped) {
						onError();
						finish();
					}
				});
			function volume(value: number, fade = 0.2) {
				if (stopped) return;
				const now = ctx.currentTime;
				gain.gain.cancelScheduledValues(now);
				gain.gain.setValueAtTime(gain.gain.value, now);
				gain.gain.linearRampToValueAtTime(value, now + fade);
			}
			return {
				volume,
				stop(fade = 0) {
					if (stopped) return;
					if (stopping) {
						if (!fade) finish();
						return;
					}
					stopping = true;
					if (!fade) finish();
					else {
						volume(0, fade);
						timer = setTimeout(finish, fade * 1000);
					}
				}
			};
		},
		dispose() {
			disposed = true;
			abort.abort();
			for (const stop of [...voices]) stop();
			buffers.clear();
			if (context) void context.close().catch(() => {});
		}
	};
}
