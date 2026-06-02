<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import {
		decodeDrawingSubmission,
		DRAWING_CANVAS_HEIGHT,
		DRAWING_CANVAS_WIDTH
	} from '$lib/drawing-codec.js';

	interface DrawingDisplayProps {
		drawing: unknown;
		className?: string;
		animate?: boolean;
		durationMs?: number;
		replayKey?: string;
	}

	let {
		drawing,
		className = '',
		animate = false,
		durationMs = 1500,
		replayKey = ''
	}: DrawingDisplayProps = $props();
	let canvas: HTMLCanvasElement;
	let animationFrame: number | null = null;

	$effect(() => {
		if (canvas) {
			startRender();
		}
	});

	onMount(() => {
		startRender();
	});

	onDestroy(() => {
		cancelReplay();
	});

	function getSubmission(value: unknown): DrawingSubmission | null {
		if (!value || typeof value !== 'object') {
			return null;
		}
		const candidate = value as Partial<DrawingSubmission>;
		if (candidate.w !== DRAWING_CANVAS_WIDTH || candidate.h !== DRAWING_CANVAS_HEIGHT) {
			return null;
		}
		if (!Array.isArray(candidate.s)) {
			return null;
		}
		return candidate as DrawingSubmission;
	}

	function startRender() {
		cancelReplay();
		const submission = getSubmission(drawing);
		if (!animate || !submission || prefersReducedMotion()) {
			renderDrawing(1);
			return;
		}
		const startedAt = performance.now();
		const duration = Math.max(100, durationMs);

		function tick(now: number) {
			const progress = Math.min(1, (now - startedAt) / duration);
			renderDrawing(progress);
			if (progress < 1) {
				animationFrame = requestAnimationFrame(tick);
			} else {
				animationFrame = null;
			}
		}

		renderDrawing(0);
		animationFrame = requestAnimationFrame(tick);
		void replayKey;
	}

	function cancelReplay() {
		if (animationFrame !== null) {
			cancelAnimationFrame(animationFrame);
			animationFrame = null;
		}
	}

	function prefersReducedMotion(): boolean {
		return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
	}

	function renderDrawing(progress = 1) {
		const context = canvas?.getContext('2d');
		if (!context) {
			return;
		}
		context.clearRect(0, 0, DRAWING_CANVAS_WIDTH, DRAWING_CANVAS_HEIGHT);
		context.fillStyle = '#ffffff';
		context.fillRect(0, 0, DRAWING_CANVAS_WIDTH, DRAWING_CANVAS_HEIGHT);
		const submission = getSubmission(drawing);
		if (!submission) {
			return;
		}
		const strokes = decodeDrawingSubmission(submission);
		const totalUnits = Math.max(
			1,
			strokes.reduce((total, stroke) => total + Math.max(1, stroke.points.length), 0)
		);
		let remainingUnits = totalUnits * Math.min(1, Math.max(0, progress));
		for (const stroke of strokes) {
			const pointCount = stroke.points.length;
			if (pointCount < 1) {
				continue;
			}
			const strokeUnits = Math.max(1, pointCount);
			if (remainingUnits <= 0) {
				break;
			}
			const visibleUnits = Math.min(strokeUnits, remainingUnits);
			remainingUnits -= strokeUnits;
			context.save();
			context.globalCompositeOperation = stroke.eraser ? 'destination-out' : 'source-over';
			context.strokeStyle = stroke.color;
			context.fillStyle = stroke.color;
			context.lineWidth = stroke.size;
			context.lineCap = 'round';
			context.lineJoin = 'round';
			context.beginPath();
			const firstPoint = stroke.points[0];
			context.moveTo(firstPoint.x * DRAWING_CANVAS_WIDTH, firstPoint.y * DRAWING_CANVAS_HEIGHT);
			if (pointCount === 1 || visibleUnits <= 1) {
				if (visibleUnits < 1) {
					context.restore();
					continue;
				}
				context.arc(
					firstPoint.x * DRAWING_CANVAS_WIDTH,
					firstPoint.y * DRAWING_CANVAS_HEIGHT,
					stroke.size / 2,
					0,
					Math.PI * 2
				);
				context.fill();
			} else {
				const fullPointCount = Math.min(pointCount - 1, Math.max(0, Math.floor(visibleUnits) - 1));
				for (let index = 1; index <= fullPointCount; index += 1) {
					const point = stroke.points[index];
					context.lineTo(point.x * DRAWING_CANVAS_WIDTH, point.y * DRAWING_CANVAS_HEIGHT);
				}
				const partialIndex = fullPointCount + 1;
				const partialProgress = visibleUnits - Math.floor(visibleUnits);
				if (partialProgress > 0 && partialIndex < pointCount) {
					const previousPoint = stroke.points[partialIndex - 1];
					const nextPoint = stroke.points[partialIndex];
					context.lineTo(
						(previousPoint.x + (nextPoint.x - previousPoint.x) * partialProgress) *
							DRAWING_CANVAS_WIDTH,
						(previousPoint.y + (nextPoint.y - previousPoint.y) * partialProgress) *
							DRAWING_CANVAS_HEIGHT
					);
				}
				context.stroke();
			}
			context.restore();
		}
	}
</script>

<canvas
	bind:this={canvas}
	class={`drawing-display ${className}`}
	width={DRAWING_CANVAS_WIDTH}
	height={DRAWING_CANVAS_HEIGHT}
	aria-hidden="true"
></canvas>

<style>
	.drawing-display {
		display: block;
		width: 100%;
		aspect-ratio: 4 / 3;
		border-radius: 0.75rem;
		background: #ffffff;
	}
</style>
