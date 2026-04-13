<script lang="ts">
	import { onDestroy } from 'svelte';

	const VIEWPORT_SIZE = 256;
	const MAX_ZOOM = 3;

	interface AvatarCropEditorProps {
		imageUrl: string;
	}

	let { imageUrl }: AvatarCropEditorProps = $props();

	let loaded = $state(false);
	let naturalWidth = $state(0);
	let naturalHeight = $state(0);
	let zoom = $state(1);
	let offsetX = $state(0);
	let offsetY = $state(0);
	let dragging = $state(false);
	let dragStartX = 0;
	let dragStartY = 0;
	let dragOriginX = 0;
	let dragOriginY = 0;

	const baseScale = $derived(
		naturalWidth > 0 && naturalHeight > 0
			? Math.max(VIEWPORT_SIZE / naturalWidth, VIEWPORT_SIZE / naturalHeight)
			: 1
	);
	const displayWidth = $derived(naturalWidth * baseScale * zoom);
	const displayHeight = $derived(naturalHeight * baseScale * zoom);
	const imageLeft = $derived((VIEWPORT_SIZE - displayWidth) / 2 + offsetX);
	const imageTop = $derived((VIEWPORT_SIZE - displayHeight) / 2 + offsetY);

	$effect(() => {
		imageUrl;
		loaded = false;
		naturalWidth = 0;
		naturalHeight = 0;
		zoom = 1;
		offsetX = 0;
		offsetY = 0;
	});

	$effect(() => {
		if (!loaded) {
			return;
		}
		constrainOffsets();
	});

	function maxOffset(horizontal: boolean) {
		const displaySize = horizontal ? displayWidth : displayHeight;
		return Math.max(0, (displaySize - VIEWPORT_SIZE) / 2);
	}

	function constrainOffsets() {
		offsetX = Math.min(maxOffset(true), Math.max(-maxOffset(true), offsetX));
		offsetY = Math.min(maxOffset(false), Math.max(-maxOffset(false), offsetY));
	}

	function onImageLoad(event: Event) {
		const target = event.currentTarget as HTMLImageElement;
		naturalWidth = target.naturalWidth;
		naturalHeight = target.naturalHeight;
		loaded = true;
	}

	function onPointerDown(event: PointerEvent) {
		if (!loaded) {
			return;
		}
		dragging = true;
		dragStartX = event.clientX;
		dragStartY = event.clientY;
		dragOriginX = offsetX;
		dragOriginY = offsetY;
		(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
	}

	function onPointerMove(event: PointerEvent) {
		if (!dragging) {
			return;
		}
		offsetX = dragOriginX + (event.clientX - dragStartX);
		offsetY = dragOriginY + (event.clientY - dragStartY);
		constrainOffsets();
	}

	function stopDragging() {
		dragging = false;
	}

	function onZoomInput(event: Event) {
		zoom = Number((event.currentTarget as HTMLInputElement).value);
	}

	export async function exportBlob(): Promise<Blob | null> {
		if (!loaded || !imageUrl) {
			return null;
		}
		const image = await loadImage(imageUrl);
		const canvas = document.createElement('canvas');
		canvas.width = VIEWPORT_SIZE;
		canvas.height = VIEWPORT_SIZE;
		const context = canvas.getContext('2d');
		if (!context) {
			return null;
		}

		const sourceX = Math.max(0, -imageLeft * (naturalWidth / displayWidth));
		const sourceY = Math.max(0, -imageTop * (naturalHeight / displayHeight));
		const sourceWidth = Math.min(naturalWidth, VIEWPORT_SIZE * (naturalWidth / displayWidth));
		const sourceHeight = Math.min(naturalHeight, VIEWPORT_SIZE * (naturalHeight / displayHeight));
		context.drawImage(
			image,
			sourceX,
			sourceY,
			sourceWidth,
			sourceHeight,
			0,
			0,
			VIEWPORT_SIZE,
			VIEWPORT_SIZE
		);

		return await new Promise<Blob | null>((resolve) => {
			canvas.toBlob((blob) => resolve(blob), 'image/png');
		});
	}

	async function loadImage(src: string) {
		return await new Promise<HTMLImageElement>((resolve, reject) => {
			const image = new Image();
			image.onload = () => resolve(image);
			image.onerror = () => reject(new Error('Could not load image.'));
			image.src = src;
		});
	}

	onDestroy(() => {
		dragging = false;
	});
</script>

<div class="crop-editor">
	<div
		class="crop-frame"
		aria-label="Avatar crop area"
		role="application"
		onpointerdown={onPointerDown}
		onpointermove={onPointerMove}
		onpointerup={stopDragging}
		onpointercancel={stopDragging}
		onpointerleave={stopDragging}
	>
		{#if imageUrl}
			<img
				class={`crop-image ${dragging ? 'dragging' : ''}`}
				src={imageUrl}
				alt="Avatar crop preview"
				onload={onImageLoad}
				draggable="false"
				style={`width:${displayWidth}px;height:${displayHeight}px;left:${imageLeft}px;top:${imageTop}px;`}
			/>
		{/if}
		<div class="crop-mask" aria-hidden="true"></div>
	</div>

	<label class="zoom-wrap" for="avatar-zoom">
		<span class="label-title">Zoom</span>
		<input
			id="avatar-zoom"
			type="range"
			min="1"
			max={MAX_ZOOM}
			step="0.01"
			value={zoom}
			oninput={onZoomInput}
		/>
	</label>
</div>

<style>
	.crop-editor {
		display: grid;
		gap: 0.85rem;
	}

	.crop-frame {
		position: relative;
		width: 256px;
		height: 256px;
		max-width: 100%;
		overflow: hidden;
		border-radius: 1.5rem;
		background:
			linear-gradient(45deg, rgb(226 232 240 / 0.95) 25%, transparent 25%),
			linear-gradient(-45deg, rgb(226 232 240 / 0.95) 25%, transparent 25%),
			linear-gradient(45deg, transparent 75%, rgb(226 232 240 / 0.95) 75%),
			linear-gradient(-45deg, transparent 75%, rgb(226 232 240 / 0.95) 75%);
		background-size: 24px 24px;
		background-position:
			0 0,
			0 12px,
			12px -12px,
			-12px 0;
		border: 1px solid rgb(148 163 184 / 0.4);
		touch-action: none;
	}

	.crop-image {
		position: absolute;
		max-width: none;
		user-select: none;
		touch-action: none;
		cursor: grab;
	}

	.crop-image.dragging {
		cursor: grabbing;
	}

	.crop-mask {
		position: absolute;
		inset: 0;
		box-shadow: inset 0 0 0 2px rgb(255 255 255 / 0.95);
		pointer-events: none;
	}

	.zoom-wrap {
		display: grid;
		gap: 0.4rem;
	}

	input[type='range'] {
		width: 100%;
	}
</style>
