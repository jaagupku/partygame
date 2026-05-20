<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

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

	const CANVAS_WIDTH = 512;
	const CANVAS_HEIGHT = 384;

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
		if (candidate.width !== CANVAS_WIDTH || candidate.height !== CANVAS_HEIGHT) {
			return null;
		}
		if (!Array.isArray(candidate.strokes)) {
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
		context.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
		context.fillStyle = '#ffffff';
		context.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
		const submission = getSubmission(drawing);
		if (!submission) {
			return;
		}
		const totalUnits = Math.max(
			1,
			submission.strokes.reduce((total, stroke) => total + Math.max(1, stroke.points.length), 0)
		);
		let remainingUnits = totalUnits * Math.min(1, Math.max(0, progress));
		for (const stroke of submission.strokes) {
			if (!stroke.points.length) {
				continue;
			}
			const strokeUnits = Math.max(1, stroke.points.length);
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
			const [firstPoint, ...points] = stroke.points;
			context.moveTo(firstPoint.x * CANVAS_WIDTH, firstPoint.y * CANVAS_HEIGHT);
			if (points.length === 0 || visibleUnits <= 1) {
				if (visibleUnits < 1) {
					context.restore();
					continue;
				}
				context.arc(
					firstPoint.x * CANVAS_WIDTH,
					firstPoint.y * CANVAS_HEIGHT,
					stroke.size / 2,
					0,
					Math.PI * 2
				);
				context.fill();
			} else {
				const fullPointCount = Math.min(points.length, Math.max(0, Math.floor(visibleUnits) - 1));
				for (const point of points.slice(0, fullPointCount)) {
					context.lineTo(point.x * CANVAS_WIDTH, point.y * CANVAS_HEIGHT);
				}
				const partialIndex = fullPointCount;
				const partialProgress = visibleUnits - Math.floor(visibleUnits);
				if (partialProgress > 0 && partialIndex < points.length) {
					const previousPoint = partialIndex === 0 ? firstPoint : points[partialIndex - 1];
					const nextPoint = points[partialIndex];
					context.lineTo(
						(previousPoint.x + (nextPoint.x - previousPoint.x) * partialProgress) * CANVAS_WIDTH,
						(previousPoint.y + (nextPoint.y - previousPoint.y) * partialProgress) * CANVAS_HEIGHT
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
	width={CANVAS_WIDTH}
	height={CANVAS_HEIGHT}
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
