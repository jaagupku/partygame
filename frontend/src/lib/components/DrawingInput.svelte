<script lang="ts">
	import 'iconify-icon';
	import { onDestroy } from 'svelte';
	import DrawingDisplay from '$lib/components/DrawingDisplay.svelte';
	import {
		DRAWING_CANVAS_HEIGHT,
		DRAWING_CANVAS_WIDTH,
		DRAWING_COLORS,
		encodeDrawingSubmission,
		simplifyDrawingPoints
	} from '$lib/drawing-codec.js';
	import { DRAWING_LIMITS, getDrawingLimitUsage } from '$lib/drawing-limits.js';
	import { messages } from '$lib/i18n';

	interface DrawingInputProps {
		disabled: boolean;
		mode?: 'live' | 'preview';
		resetKey?: string;
		showSubmit?: boolean;
		submitPosition?: 'top' | 'bottom';
		onSubmit: (drawing: DrawingSubmission) => void;
	}

	let {
		disabled,
		mode = 'live',
		resetKey = '',
		showSubmit = true,
		submitPosition = 'bottom',
		onSubmit
	}: DrawingInputProps = $props();
	let canvas: HTMLCanvasElement;
	let selectedColor = $state('#0f172a');
	let eraserEnabled = $state(false);
	let brushControlsOpen = $state(false);
	let brushSize = $state(8);
	let strokes = $state<DrawingStroke[]>([]);
	let redoStrokes = $state<DrawingStroke[]>([]);
	let activeStroke = $state<DrawingStroke | null>(null);
	let clearConfirming = $state(false);
	let clearConfirmTimeout: number | null = null;
	let lastResetKey = $state<string | undefined>(undefined);

	const hasDrawing = $derived(strokes.length > 0);
	const canUndo = $derived(strokes.length > 0);
	const canRedo = $derived(redoStrokes.length > 0);
	const submission = $derived<DrawingSubmission>(buildPreviewSubmission());
	const limitUsage = $derived(getDrawingLimitUsage(submission));
	const submitDisabled = $derived(mode === 'preview' || limitUsage.overLimit);

	onDestroy(() => {
		resetClearConfirmation();
	});

	$effect(() => {
		if (lastResetKey === undefined) {
			lastResetKey = resetKey;
			return;
		}
		if (resetKey === lastResetKey) {
			return;
		}
		lastResetKey = resetKey;
		resetDrawing();
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
		if (redoStrokes.length > 0) {
			redoStrokes = [];
		}
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
		if (activeStroke) {
			const simplifiedStroke = {
				...activeStroke,
				points: simplifyDrawingPoints(activeStroke.points)
			};
			strokes = [...strokes.slice(0, -1), simplifiedStroke];
		}
		activeStroke = null;
	}

	function undoStroke() {
		if (disabled || !canUndo) {
			return;
		}
		const undoneStroke = strokes.at(-1);
		if (!undoneStroke) {
			return;
		}
		resetClearConfirmation();
		activeStroke = null;
		strokes = strokes.slice(0, -1);
		redoStrokes = [...redoStrokes, undoneStroke];
	}

	function redoStroke() {
		if (disabled || !canRedo) {
			return;
		}
		const redoneStroke = redoStrokes.at(-1);
		if (!redoneStroke) {
			return;
		}
		resetClearConfirmation();
		activeStroke = null;
		redoStrokes = redoStrokes.slice(0, -1);
		strokes = [...strokes, redoneStroke];
	}

	function clearDrawing() {
		if (disabled) {
			return;
		}
		if (!clearConfirming) {
			clearConfirming = true;
			if (clearConfirmTimeout !== null) {
				window.clearTimeout(clearConfirmTimeout);
			}
			clearConfirmTimeout = window.setTimeout(() => {
				clearConfirming = false;
				clearConfirmTimeout = null;
			}, 2200);
			return;
		}
		resetClearConfirmation();
		resetDrawing();
	}

	function resetDrawing() {
		strokes = [];
		redoStrokes = [];
		activeStroke = null;
		resetClearConfirmation();
	}

	function resetClearConfirmation() {
		if (clearConfirmTimeout !== null) {
			window.clearTimeout(clearConfirmTimeout);
			clearConfirmTimeout = null;
		}
		clearConfirming = false;
	}

	function buildSubmission(): DrawingSubmission {
		return encodeDrawingSubmission(strokes);
	}

	function buildPreviewSubmission(): DrawingSubmission {
		return encodeDrawingSubmission(strokes, { simplify: false });
	}

	export function getDraftSubmission(): DrawingSubmission | undefined {
		if (!hasDrawing) {
			return undefined;
		}
		return buildSubmission();
	}

	function submitDrawing() {
		if (disabled || submitDisabled || !hasDrawing) {
			return;
		}
		onSubmit(buildSubmission());
	}
</script>

<div class="drawing-input-root">
	{#if showSubmit && submitPosition === 'top'}
		<button
			type="button"
			class="btn btn-primary controller-primary-action drawing-submit-button"
			onclick={submitDrawing}
			disabled={disabled || submitDisabled || !hasDrawing}
		>
			{$messages.gameplay.submitDrawing}
		</button>
	{/if}
	<div class="drawing-input-shell">
		<DrawingDisplay drawing={submission} className="drawing-input-display" />
		<canvas
			bind:this={canvas}
			class="drawing-input-canvas"
			width={DRAWING_CANVAS_WIDTH}
			height={DRAWING_CANVAS_HEIGHT}
			onpointerdown={beginStroke}
			onpointermove={continueStroke}
			onpointerup={endStroke}
			onpointercancel={endStroke}
			onpointerleave={endStroke}
		></canvas>
	</div>
	<div class="drawing-tools">
		<div class="drawing-colors" aria-label={$messages.gameplay.drawingAnswer}>
			{#each DRAWING_COLORS as color}
				<button
					type="button"
					class={`drawing-color ${selectedColor === color && !eraserEnabled ? 'drawing-color-active' : ''}`}
					style={`--drawing-color: ${color}`}
					aria-label={$messages.gameplay.drawingColor(color)}
					{disabled}
					onclick={() => {
						selectedColor = color;
						eraserEnabled = false;
						brushControlsOpen = false;
						resetClearConfirmation();
					}}
				></button>
			{/each}
		</div>
		<div class="drawing-tool-actions">
			<button
				type="button"
				class="controller-icon-button"
				disabled={disabled || !canUndo}
				onclick={undoStroke}
				aria-label={$messages.gameplay.undoDrawingStroke}
				title={$messages.gameplay.undoDrawingStroke}
			>
				<iconify-icon icon="fluent:arrow-undo-20-filled"></iconify-icon>
			</button>
			<button
				type="button"
				class="controller-icon-button"
				disabled={disabled || !canRedo}
				onclick={redoStroke}
				aria-label={$messages.gameplay.redoDrawingStroke}
				title={$messages.gameplay.redoDrawingStroke}
			>
				<iconify-icon icon="fluent:arrow-redo-20-filled"></iconify-icon>
			</button>
			<button
				type="button"
				class={`controller-icon-button ${eraserEnabled ? 'controller-icon-button-active' : ''}`}
				{disabled}
				onclick={() => {
					eraserEnabled = !eraserEnabled;
					brushControlsOpen = false;
					resetClearConfirmation();
				}}
				aria-label={$messages.gameplay.eraser}
				title={$messages.gameplay.eraser}
			>
				<iconify-icon icon="fluent:eraser-20-regular"></iconify-icon>
			</button>
			<button
				type="button"
				class={`controller-icon-button ${brushControlsOpen ? 'controller-icon-button-active' : ''}`}
				{disabled}
				onclick={() => {
					brushControlsOpen = !brushControlsOpen;
					resetClearConfirmation();
				}}
				aria-label={$messages.gameplay.brushSize}
				aria-expanded={brushControlsOpen}
				title={$messages.gameplay.brushSize}
			>
				<iconify-icon icon="fluent:paint-brush-20-filled"></iconify-icon>
			</button>
			<button
				type="button"
				class={`controller-icon-button drawing-clear-button ${clearConfirming ? 'drawing-clear-button-confirm' : ''}`}
				disabled={disabled || !hasDrawing}
				onclick={clearDrawing}
				aria-label={clearConfirming
					? `${$messages.gameplay.clearDrawing}?`
					: $messages.gameplay.clearDrawing}
				title={clearConfirming
					? `${$messages.gameplay.clearDrawing}?`
					: $messages.gameplay.clearDrawing}
			>
				<iconify-icon
					icon={clearConfirming ? 'fluent:checkmark-20-filled' : 'fluent:delete-20-filled'}
				></iconify-icon>
			</button>
		</div>
	</div>
	{#if brushControlsOpen}
		<label class="drawing-brush-control">
			<span>{$messages.gameplay.brushSize}</span>
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
	{/if}
	{#if hasDrawing}
		<p
			class={`drawing-limit-status ${
				limitUsage.overLimit
					? 'drawing-limit-status-error'
					: limitUsage.nearLimit
						? 'drawing-limit-status-warning'
						: ''
			}`}
			role={limitUsage.overLimit ? 'alert' : 'status'}
		>
			{#if limitUsage.overLimit}
				{$messages.gameplay.drawingLimitExceeded(
					limitUsage.strokes,
					DRAWING_LIMITS.maxStrokes,
					limitUsage.points,
					DRAWING_LIMITS.maxPoints
				)}
			{:else if limitUsage.nearLimit}
				{$messages.gameplay.drawingLimitWarning(
					limitUsage.strokes,
					DRAWING_LIMITS.maxStrokes,
					limitUsage.points,
					DRAWING_LIMITS.maxPoints
				)}
			{:else}
				{$messages.gameplay.drawingLimitUsage(
					limitUsage.strokes,
					DRAWING_LIMITS.maxStrokes,
					limitUsage.points,
					DRAWING_LIMITS.maxPoints
				)}
			{/if}
		</p>
	{/if}
	{#if showSubmit && submitPosition === 'bottom'}
		<button
			type="button"
			class="btn btn-primary controller-primary-action drawing-submit-button"
			onclick={submitDrawing}
			disabled={disabled || submitDisabled || !hasDrawing}
		>
			{$messages.gameplay.submitDrawing}
		</button>
	{/if}
</div>

<style>
	.drawing-input-root {
		display: flex;
		flex-direction: column;
		gap: 0.65rem;
	}

	.drawing-submit-button {
		width: 100%;
	}

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
		width: 2rem;
		height: 2rem;
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

	.drawing-tools {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.drawing-colors {
		display: flex;
		min-width: 0;
		width: 100%;
		gap: 0.4rem;
		overflow-x: auto;
		padding-block: 0.15rem;
		scrollbar-width: none;
	}

	.drawing-colors::-webkit-scrollbar {
		display: none;
	}

	.drawing-tool-actions {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		width: 100%;
	}

	.drawing-clear-button {
		margin-left: auto;
	}

	.drawing-clear-button-confirm {
		border-color: rgba(239, 68, 68, 0.44);
		background: rgb(254 226 226);
		color: rgb(185 28 28);
	}

	.drawing-brush-control {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		align-items: center;
		gap: 0.75rem;
		color: rgb(51 65 85);
		font-size: 0.85rem;
		font-weight: 800;
	}

	.drawing-brush-control :global(.number-slider) {
		min-height: 1.75rem;
	}

	.drawing-limit-status {
		font-size: 0.75rem;
		font-weight: 700;
		color: rgb(71 85 105);
	}

	.drawing-limit-status-warning {
		color: rgb(180 83 9);
	}

	.drawing-limit-status-error {
		color: rgb(185 28 28);
	}

	@media (max-width: 640px) {
		.drawing-input-root {
			gap: 0.5rem;
		}

		.drawing-input-shell {
			border-radius: 0.75rem;
		}

		.drawing-color {
			width: 1.85rem;
			height: 1.85rem;
		}
	}
</style>
