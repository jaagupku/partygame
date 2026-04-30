<script lang="ts">
	import { DEFAULT_REVEAL_CURVE, normalizeRevealCurve } from '$lib/media/image-reveal';
	import { messages } from '$lib/i18n';

	type CurveKey = 'blur_reveal_curve' | 'blur_circle_reveal_curve' | 'zoom_reveal_curve';

	type Props = {
		media: ImageMediaDefinition;
		curveKey: CurveKey;
		label: string;
		help: string;
	};

	let { media, curveKey, label, help }: Props = $props();
	let activeHandle = $state<0 | 1 | null>(null);
	let graphElement = $state<SVGSVGElement | null>(null);

	const graphSize = 100;
	const curve = $derived(normalizeRevealCurve(media[curveKey]));
	const curvePath = $derived(
		`M 0 ${graphSize} C ${curve[0] * graphSize} ${(1 - curve[1]) * graphSize}, ${
			curve[2] * graphSize
		} ${(1 - curve[3]) * graphSize}, ${graphSize} 0`
	);

	function setCurve(nextCurve: RevealCurve | undefined) {
		media[curveKey] = nextCurve;
	}

	function updateCurveValue(index: number, value: number) {
		const nextCurve = [...curve] as RevealCurve;
		nextCurve[index] = Math.min(1, Math.max(0, Number.isFinite(value) ? value : 0));
		setCurve(nextCurve);
	}

	function setHandleFromPointer(event: PointerEvent, handle: 0 | 1) {
		const rect = graphElement?.getBoundingClientRect();
		if (!rect) {
			return;
		}
		if (rect.width <= 0 || rect.height <= 0) {
			return;
		}
		const x = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
		const y = Math.min(1, Math.max(0, 1 - (event.clientY - rect.top) / rect.height));
		const baseIndex = handle === 0 ? 0 : 2;
		const nextCurve = [...curve] as RevealCurve;
		nextCurve[baseIndex] = x;
		nextCurve[baseIndex + 1] = y;
		setCurve(nextCurve);
	}

	function startDrag(event: PointerEvent, handle: 0 | 1) {
		activeHandle = handle;
		try {
			graphElement?.setPointerCapture(event.pointerId);
		} catch {
			// Pointer capture can fail in synthetic test environments.
		}
		setHandleFromPointer(event, handle);
	}

	function dragHandle(event: PointerEvent) {
		if (activeHandle === null) {
			return;
		}
		setHandleFromPointer(event, activeHandle);
	}

	function stopDrag() {
		activeHandle = null;
	}

	function nudgeHandle(event: KeyboardEvent, handle: 0 | 1) {
		const step = event.shiftKey ? 0.1 : 0.01;
		let deltaX = 0;
		let deltaY = 0;
		if (event.key === 'ArrowLeft') {
			deltaX = -step;
		} else if (event.key === 'ArrowRight') {
			deltaX = step;
		} else if (event.key === 'ArrowDown') {
			deltaY = -step;
		} else if (event.key === 'ArrowUp') {
			deltaY = step;
		} else {
			return;
		}
		event.preventDefault();
		const baseIndex = handle === 0 ? 0 : 2;
		const nextCurve = [...curve] as RevealCurve;
		nextCurve[baseIndex] = Math.min(1, Math.max(0, nextCurve[baseIndex] + deltaX));
		nextCurve[baseIndex + 1] = Math.min(1, Math.max(0, nextCurve[baseIndex + 1] + deltaY));
		setCurve(nextCurve);
	}

	function resetCurve() {
		setCurve(undefined);
	}
</script>

<div class="grid gap-3 rounded-2xl bg-white p-4">
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div>
			<p class="text-sm font-bold uppercase tracking-wide text-slate-500">{label}</p>
			<p class="mt-1 text-sm text-slate-500">{help}</p>
		</div>
		<button class="btn btn-ghost text-sm" type="button" onclick={resetCurve}>
			{$messages.editor.resetRevealCurve}
		</button>
	</div>

	<div class="grid gap-4 md:grid-cols-[minmax(0,14rem)_1fr]">
		<svg
			class="h-56 w-full touch-none rounded-2xl border border-slate-200 bg-slate-50 p-3"
			viewBox="-6 -6 112 112"
			role="img"
			aria-label={label}
			bind:this={graphElement}
			onpointermove={dragHandle}
			onpointerup={stopDrag}
			onpointercancel={stopDrag}
			onpointerleave={stopDrag}
		>
			<path d="M 0 100 L 100 0" stroke="rgb(203 213 225)" stroke-width="1" />
			<path d={curvePath} fill="none" stroke="rgb(14 165 233)" stroke-width="4" />
			<line
				x1="0"
				y1="100"
				x2={curve[0] * graphSize}
				y2={(1 - curve[1]) * graphSize}
				stroke="rgb(148 163 184)"
				stroke-width="1.5"
			/>
			<line
				x1="100"
				y1="0"
				x2={curve[2] * graphSize}
				y2={(1 - curve[3]) * graphSize}
				stroke="rgb(148 163 184)"
				stroke-width="1.5"
			/>
			<circle cx="0" cy="100" r="2.5" fill="rgb(15 23 42)" />
			<circle cx="100" cy="0" r="2.5" fill="rgb(15 23 42)" />
			<circle
				cx={curve[0] * graphSize}
				cy={(1 - curve[1]) * graphSize}
				r="5"
				fill="white"
				stroke="rgb(14 165 233)"
				stroke-width="3"
				role="slider"
				tabindex="0"
				aria-label={`${label} control point 1`}
				aria-valuemin="0"
				aria-valuemax="1"
				aria-valuenow={curve[0]}
				onpointerdown={(event) => startDrag(event, 0)}
				onkeydown={(event) => nudgeHandle(event, 0)}
			/>
			<circle
				cx={curve[2] * graphSize}
				cy={(1 - curve[3]) * graphSize}
				r="5"
				fill="white"
				stroke="rgb(14 165 233)"
				stroke-width="3"
				role="slider"
				tabindex="0"
				aria-label={`${label} control point 2`}
				aria-valuemin="0"
				aria-valuemax="1"
				aria-valuenow={curve[2]}
				onpointerdown={(event) => startDrag(event, 1)}
				onkeydown={(event) => nudgeHandle(event, 1)}
			/>
		</svg>

		<div class="grid grid-cols-2 gap-3">
			{#each DEFAULT_REVEAL_CURVE as _, index}
				<label class="grid gap-1">
					<span class="text-xs font-bold uppercase tracking-wide text-slate-500">
						{['X1', 'Y1', 'X2', 'Y2'][index]}
					</span>
					<input
						type="number"
						min="0"
						max="1"
						step="0.01"
						class="input text-base"
						value={curve[index]}
						oninput={(event) =>
							updateCurveValue(index, Number((event.currentTarget as HTMLInputElement).value))}
					/>
				</label>
			{/each}
		</div>
	</div>
</div>
