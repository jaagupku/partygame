<script lang="ts">
	import 'iconify-icon';
	import { flip } from 'svelte/animate';

	type OrderingListVariant = 'player' | 'editor';

	type Props = {
		items: string[];
		disabled?: boolean;
		variant?: OrderingListVariant;
		dragLabel: string;
		moveUpLabel: string;
		moveDownLabel: string;
		onReorder: (items: string[]) => void;
	};

	let {
		items,
		disabled = false,
		variant = 'player',
		dragLabel,
		moveUpLabel,
		moveDownLabel,
		onReorder
	}: Props = $props();

	let draggedIndex = $state<number | null>(null);
	let dropIndex = $state<number | null>(null);
	let dragPointerId = $state<number | null>(null);
	let listElement = $state<HTMLDivElement | null>(null);
	let movedItemKey = $state<string | null>(null);

	const rowLayoutClass = $derived(
		variant === 'editor'
			? 'grid gap-3 rounded-2xl border bg-white p-3 transition md:grid-cols-[auto_auto_1fr_auto]'
			: 'flex items-center gap-3 rounded-2xl border p-3 transition'
	);
	const idleRowClass = $derived(
		variant === 'editor' ? 'border-slate-200' : 'border-white/70 bg-white/70'
	);
	const draggedRowClass = $derived(
		variant === 'editor'
			? 'border-amber-300 bg-amber-50 opacity-80'
			: 'border-sky-300 bg-sky-50 opacity-80'
	);
	const dropRowClass = $derived(
		variant === 'editor' ? 'border-amber-200 bg-amber-50/70' : 'border-sky-200 bg-sky-50/70'
	);
	const badgeClass = $derived(
		variant === 'editor'
			? 'inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-50 text-sm font-bold text-amber-700'
			: 'badge bg-slate-100 text-slate-700'
	);
	const handleClass = $derived(
		variant === 'editor'
			? 'inline-flex h-11 w-11 cursor-grab touch-none select-none items-center justify-center rounded-2xl bg-slate-100 text-slate-500 active:cursor-grabbing disabled:cursor-default disabled:opacity-40'
			: 'inline-flex h-10 w-10 cursor-grab touch-none select-none items-center justify-center rounded-xl bg-slate-100 text-slate-500 active:cursor-grabbing disabled:cursor-default disabled:opacity-40'
	);
	const itemClass = $derived(
		variant === 'editor'
			? 'min-w-0 rounded-2xl bg-slate-50 px-4 py-3 text-lg font-semibold text-slate-900'
			: 'flex-1 font-semibold'
	);
	const moveButtonClass = $derived(
		variant === 'editor' ? 'btn btn-ghost h-11 w-11 p-0' : 'btn btn-ghost h-10 w-10 p-0'
	);

	function reorderItems(fromIndex: number, toIndex: number) {
		if (
			disabled ||
			fromIndex === toIndex ||
			fromIndex < 0 ||
			toIndex < 0 ||
			fromIndex >= items.length ||
			toIndex >= items.length
		) {
			return;
		}
		const next = [...items];
		const [movedItem] = next.splice(fromIndex, 1);
		next.splice(toIndex, 0, movedItem);
		onReorder(next);
	}

	function moveItem(index: number, direction: -1 | 1) {
		const nextIndex = index + direction;
		movedItemKey = itemKey(items[index], index);
		reorderItems(index, index + direction);
		window.setTimeout(() => {
			movedItemKey = null;
		}, 420);
	}

	function itemKey(item: string, index: number) {
		const occurrence = items.slice(0, index + 1).filter((value) => value === item).length;
		return `${item}::${occurrence}`;
	}

	function startDrag(index: number) {
		if (disabled) {
			return;
		}
		draggedIndex = index;
		dropIndex = index;
	}

	function updateDropTarget(index: number) {
		if (disabled || draggedIndex === null) {
			return;
		}
		dropIndex = index;
	}

	function indexFromPointer(clientY: number) {
		const rows = Array.from(
			listElement?.querySelectorAll<HTMLElement>('[data-ordering-index]') ?? []
		);
		if (rows.length === 0) {
			return null;
		}
		for (const row of rows) {
			const index = Number(row.dataset.orderingIndex);
			const rect = row.getBoundingClientRect();
			if (clientY < rect.top + rect.height / 2) {
				return index;
			}
		}
		return Number(rows[rows.length - 1].dataset.orderingIndex);
	}

	function startPointerDrag(event: PointerEvent, index: number) {
		if (disabled) {
			return;
		}
		event.preventDefault();
		dragPointerId = event.pointerId;
		(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
		draggedIndex = index;
		dropIndex = index;
	}

	function updatePointerDrag(event: PointerEvent) {
		if (disabled || dragPointerId !== event.pointerId) {
			return;
		}
		event.preventDefault();
		const targetIndex = indexFromPointer(event.clientY);
		if (targetIndex !== null) {
			dropIndex = targetIndex;
		}
	}

	function finishPointerDrag(event: PointerEvent) {
		if (dragPointerId !== event.pointerId) {
			return;
		}
		event.preventDefault();
		if (draggedIndex !== null && dropIndex !== null) {
			reorderItems(draggedIndex, dropIndex);
		}
		cancelPointerDrag(event);
	}

	function cancelPointerDrag(event?: PointerEvent) {
		if (event && dragPointerId === event.pointerId) {
			try {
				(event.currentTarget as HTMLElement).releasePointerCapture(event.pointerId);
			} catch {
				// The pointer may already be released if the browser cancelled the gesture.
			}
		}
		dragPointerId = null;
		draggedIndex = null;
		dropIndex = null;
	}

	function finishDrop(index: number) {
		if (disabled || draggedIndex === null) {
			cancelDrag();
			return;
		}
		reorderItems(draggedIndex, index);
		cancelDrag();
	}

	function cancelDrag() {
		draggedIndex = null;
		dropIndex = null;
	}
</script>

<div class={variant === 'editor' ? 'grid gap-3' : 'stack-md'} bind:this={listElement}>
	{#each items as item, index (itemKey(item, index))}
		<div
			class={`${rowLayoutClass} ${
				draggedIndex === index ? draggedRowClass : dropIndex === index ? dropRowClass : idleRowClass
			} ${movedItemKey === itemKey(item, index) ? 'ordering-row-moved' : ''}`}
			animate:flip={{ duration: 220 }}
			role="listitem"
			data-ordering-index={index}
			aria-grabbed={draggedIndex === index}
			draggable={!disabled}
			ondragstart={() => startDrag(index)}
			ondragover={(event) => {
				event.preventDefault();
				updateDropTarget(index);
			}}
			ondrop={(event) => {
				event.preventDefault();
				finishDrop(index);
			}}
			ondragend={cancelDrag}
		>
			<div class={badgeClass}>{variant === 'player' ? `#${index + 1}` : index + 1}</div>
			<button
				type="button"
				class={handleClass}
				{disabled}
				aria-label={dragLabel}
				title={dragLabel}
				onpointerdown={(event) => startPointerDrag(event, index)}
				onpointermove={updatePointerDrag}
				onpointerup={finishPointerDrag}
				onpointercancel={cancelPointerDrag}
			>
				::
			</button>
			<div class={itemClass}>{item}</div>
			<div class="flex shrink-0 gap-2">
				<button
					type="button"
					class={moveButtonClass}
					disabled={disabled || index === 0}
					onclick={() => moveItem(index, -1)}
					aria-label={moveUpLabel}
					title={moveUpLabel}
				>
					<iconify-icon icon="fluent:arrow-up-16-filled"></iconify-icon>
				</button>
				<button
					type="button"
					class={moveButtonClass}
					disabled={disabled || index === items.length - 1}
					onclick={() => moveItem(index, 1)}
					aria-label={moveDownLabel}
					title={moveDownLabel}
				>
					<iconify-icon icon="fluent:arrow-down-16-filled"></iconify-icon>
				</button>
			</div>
		</div>
	{/each}
</div>

<style>
	.ordering-row-moved {
		animation: ordering-row-moved 360ms ease-out both;
	}

	@keyframes ordering-row-moved {
		0% {
			filter: brightness(1);
			box-shadow: 0 0 0 rgb(14 165 233 / 0);
		}

		45% {
			filter: brightness(1.06);
			box-shadow: 0 0 24px rgb(14 165 233 / 0.22);
		}

		100% {
			filter: brightness(1);
			box-shadow: 0 0 0 rgb(14 165 233 / 0);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.ordering-row-moved {
			animation: none;
		}
	}
</style>
