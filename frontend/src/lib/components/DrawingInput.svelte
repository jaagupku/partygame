<script lang="ts">
	import DrawingDisplay from '$lib/components/DrawingDisplay.svelte';
	import { messages } from '$lib/i18n';

	interface DrawingInputProps {
		disabled: boolean;
		onSubmit: (drawing: DrawingSubmission) => void;
	}

	let { disabled, onSubmit }: DrawingInputProps = $props();
	let canvas: HTMLCanvasElement;
	let selectedColor = $state('#0f172a');
	let eraserEnabled = $state(false);
	let brushSize = $state(8);
	let strokes = $state<DrawingStroke[]>([]);
	let activeStroke = $state<DrawingStroke | null>(null);

	const CANVAS_WIDTH = 512;
	const CANVAS_HEIGHT = 384;
	const COLORS = [
		'#0f172a',
		'#ef4444',
		'#f97316',
		'#eab308',
		'#22c55e',
		'#06b6d4',
		'#3b82f6',
		'#a855f7',
		'#ec4899',
		'#ffffff'
	];

	const hasDrawing = $derived(strokes.length > 0);
	const submission = $derived<DrawingSubmission>({
		width: CANVAS_WIDTH,
		height: CANVAS_HEIGHT,
		strokes
	});

	function pointFromEvent(event: PointerEvent): DrawingPoint {
		const rect = canvas.getBoundingClientRect();
		return {
			x: Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width)),
			y: Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height))
		};
	}

	function beginStroke(event: PointerEvent) {
		if (disabled) {
			return;
		}
		canvas.setPointerCapture(event.pointerId);
		const stroke: DrawingStroke = {
			color: eraserEnabled ? '#ffffff' : selectedColor,
			size: eraserEnabled ? Math.max(Number(brushSize) * 2, 16) : Number(brushSize),
			eraser: eraserEnabled,
			points: [pointFromEvent(event)]
		};
		activeStroke = stroke;
		strokes = [...strokes, stroke];
	}

	function continueStroke(event: PointerEvent) {
		if (!activeStroke || disabled) {
			return;
		}
		const point = pointFromEvent(event);
		const lastPoint = activeStroke.points.at(-1);
		if (lastPoint && Math.hypot(point.x - lastPoint.x, point.y - lastPoint.y) < 0.004) {
			return;
		}
		activeStroke.points = [...activeStroke.points, point];
		strokes = [...strokes.slice(0, -1), activeStroke];
	}

	function endStroke() {
		activeStroke = null;
	}

	function clearDrawing() {
		if (disabled) {
			return;
		}
		strokes = [];
		activeStroke = null;
	}

	function submitDrawing() {
		if (disabled || !hasDrawing) {
			return;
		}
		onSubmit(submission);
	}
</script>

<div class="stack-md">
	<div class="drawing-input-shell">
		<DrawingDisplay drawing={submission} />
		<canvas
			bind:this={canvas}
			class="drawing-input-canvas"
			width={CANVAS_WIDTH}
			height={CANVAS_HEIGHT}
			onpointerdown={beginStroke}
			onpointermove={continueStroke}
			onpointerup={endStroke}
			onpointercancel={endStroke}
			onpointerleave={endStroke}
		></canvas>
	</div>
	<div class="flex flex-wrap items-center gap-2">
		{#each COLORS as color}
			<button
				type="button"
				class={`drawing-color ${selectedColor === color && !eraserEnabled ? 'drawing-color-active' : ''}`}
				style={`--drawing-color: ${color}`}
				aria-label={$messages.gameplay.drawingColor(color)}
				{disabled}
				onclick={() => {
					selectedColor = color;
					eraserEnabled = false;
				}}
			></button>
		{/each}
		<button
			type="button"
			class={`btn ${eraserEnabled ? 'btn-primary' : 'btn-ghost'}`}
			{disabled}
			onclick={() => (eraserEnabled = !eraserEnabled)}
		>
			{$messages.gameplay.eraser}
		</button>
		<button
			type="button"
			class="btn btn-ghost"
			disabled={disabled || !hasDrawing}
			onclick={clearDrawing}
		>
			{$messages.gameplay.clearDrawing}
		</button>
	</div>
	<label class="grid gap-2 text-sm font-bold text-slate-700">
		{$messages.gameplay.brushSize}
		<input
			class="number-slider"
			type="range"
			min="2"
			max="16"
			step="1"
			bind:value={brushSize}
			{disabled}
		/>
	</label>
	<button
		type="button"
		class="btn btn-primary"
		onclick={submitDrawing}
		disabled={disabled || !hasDrawing}
	>
		{$messages.gameplay.submitDrawing}
	</button>
</div>

<style>
	.drawing-input-shell {
		position: relative;
		overflow: hidden;
		border-radius: 0.9rem;
		border: 1px solid rgb(203 213 225);
		background: #ffffff;
		touch-action: none;
	}

	.drawing-input-canvas {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		touch-action: none;
		cursor: crosshair;
	}

	.drawing-color {
		width: 2.35rem;
		height: 2.35rem;
		border-radius: 999px;
		border: 2px solid rgb(226 232 240);
		background: var(--drawing-color);
		box-shadow: inset 0 0 0 1px rgb(15 23 42 / 0.08);
	}

	.drawing-color-active {
		border-color: rgb(37 99 235);
		box-shadow:
			0 0 0 3px rgb(191 219 254),
			inset 0 0 0 1px rgb(15 23 42 / 0.12);
	}
</style>
