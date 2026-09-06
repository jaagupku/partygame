<script lang="ts">
	import { tick, untrack } from 'svelte';
	import { flip } from 'svelte/animate';
	import 'iconify-icon';
	import { stepBadges, stepPreview } from './helpers';
	import type { FlatStepItem } from './types';

	type Props = {
		rounds: RoundDefinition[];
		flatSteps: FlatStepItem[];
		selectedStepKey: string | null;
		draggedStepKey: string | null;
		dropTargetKey: string | null;
		draggedItem: FlatStepItem | null;
		dragPointerX: number;
		dragPointerY: number;
		dragOffsetX: number;
		dragOffsetY: number;
		dragCardWidth: number;
		onSelectStep: (stepKey: string | undefined) => void;
		onOpenRoundModal: (roundIndex: number) => void;
		moveRound: (roundIndex: number, direction: -1 | 1) => void;
		onRemoveRound: (roundIndex: number) => void;
		onStepDragStart: (event: PointerEvent, stepKey: string) => void;
		onStepDragMove: (event: PointerEvent) => void;
		onStepDragEnd: () => void;
		onActivateDropTarget: (key: string | null) => void;
		onDropStep: (targetRoundIndex: number, targetStepIndex: number, key: string) => void;
	};

	let {
		rounds,
		flatSteps,
		selectedStepKey,
		draggedStepKey,
		dropTargetKey,
		draggedItem,
		dragPointerX,
		dragPointerY,
		dragOffsetX,
		dragOffsetY,
		dragCardWidth,
		onSelectStep,
		onOpenRoundModal,
		moveRound,
		onRemoveRound,
		onStepDragStart,
		onStepDragMove,
		onStepDragEnd,
		onActivateDropTarget,
		onDropStep
	}: Props = $props();

	let sorterScroller = $state<HTMLDivElement | null>(null);
	let activeDropTarget = $state<{ key: string; roundIndex: number; stepIndex: number } | null>(
		null
	);

	$effect(() => {
		const stepKey = selectedStepKey;
		const scroller = sorterScroller;
		if (!stepKey || !scroller || untrack(() => pointerId !== null)) {
			return;
		}

		void tick().then(() => {
			if (pointerId !== null) return;
			const selectedCard = scroller.querySelector<HTMLElement>(`[data-step-key="${stepKey}"]`);
			if (!selectedCard) {
				return;
			}

			const scrollerRect = scroller.getBoundingClientRect();
			const cardRect = selectedCard.getBoundingClientRect();
			const isVisible = cardRect.top >= scrollerRect.top && cardRect.bottom <= scrollerRect.bottom;

			if (!isVisible) {
				selectedCard.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
			}
		});
	});

	function buildDropTarget(roundIndex: number, stepIndex: number) {
		return {
			key: `round-${roundIndex}-index-${stepIndex}`,
			roundIndex,
			stepIndex
		};
	}

	function isDropTargetActive(roundIndex: number, stepIndex: number) {
		return Boolean(draggedStepKey && dropTargetKey === buildDropTarget(roundIndex, stepIndex).key);
	}

	function parseDropTarget(element: HTMLElement | null, pointerY: number) {
		const emptyRound = element?.closest<HTMLElement>('[data-empty-round-target]');
		if (emptyRound) {
			const roundIndex = Number(emptyRound.dataset.roundIndex);
			if (!Number.isNaN(roundIndex)) {
				return buildDropTarget(roundIndex, 0);
			}
		}

		const stepCard = element?.closest<HTMLElement>('[data-step-card]');
		if (stepCard) {
			const roundIndex = Number(stepCard.dataset.roundIndex);
			const stepIndex = Number(stepCard.dataset.stepIndex);
			if (Number.isNaN(roundIndex) || Number.isNaN(stepIndex)) {
				return null;
			}

			const rect = stepCard.getBoundingClientRect();
			const insertIndex =
				rect.height > 0 && pointerY > rect.top + rect.height / 2 ? stepIndex + 1 : stepIndex;
			return buildDropTarget(roundIndex, insertIndex);
		}

		return null;
	}

	let pointerId: number | null = null;
	let pointerX = 0;
	let pointerY = 0;
	let suppressClick = false;
	let captureCard: HTMLElement | null = null;

	function updateDropTarget() {
		const rect = sorterScroller?.getBoundingClientRect();
		const inside =
			rect &&
			pointerX >= rect.left &&
			pointerX <= rect.right &&
			pointerY >= rect.top &&
			pointerY <= rect.bottom;
		activeDropTarget = inside
			? parseDropTarget(
					document.elementFromPoint(pointerX, pointerY) as HTMLElement | null,
					pointerY
				)
			: null;
		onActivateDropTarget(activeDropTarget?.key ?? null);
	}

	$effect(() => {
		if (!draggedStepKey || !sorterScroller) return;
		const scroller = sorterScroller;
		let frame: number;
		let previousTime = 0;
		function scroll(time: number) {
			const elapsed = previousTime ? Math.min(time - previousTime, 32) : 0;
			previousTime = time;
			const rect = scroller.getBoundingClientRect();
			if (
				pointerX >= rect.left &&
				pointerX <= rect.right &&
				pointerY >= rect.top &&
				pointerY <= rect.bottom
			) {
				const edge = Math.min(72, rect.height / 3);
				const speed =
					pointerY < rect.top + edge
						? -Math.min(1, (rect.top + edge - pointerY) / edge)
						: pointerY > rect.bottom - edge
							? Math.min(1, (pointerY - rect.bottom + edge) / edge)
							: 0;
				const before = scroller.scrollTop;
				scroller.scrollTop += speed * elapsed * 0.7;
				if (scroller.scrollTop !== before) updateDropTarget();
			}
			frame = requestAnimationFrame(scroll);
		}
		frame = requestAnimationFrame(scroll);
		return () => cancelAnimationFrame(frame);
	});

	function handlePointerDown(event: PointerEvent, stepKey: string) {
		if (event.button !== 0 || pointerId !== null) return;
		pointerId = event.pointerId;
		pointerX = event.clientX;
		pointerY = event.clientY;
		suppressClick = false;
		captureCard = event.currentTarget as HTMLElement;
		captureCard.setPointerCapture?.(event.pointerId);
		onStepDragStart(event, stepKey);
	}

	function handleWindowPointerMove(event: PointerEvent) {
		if (event.pointerId !== pointerId) return;
		pointerX = event.clientX;
		pointerY = event.clientY;
		onStepDragMove(event);
		// Parent props settle on the next Svelte update, including drag activation.
		void tick().then(() => {
			if (pointerId === null || !draggedStepKey) return;
			suppressClick = true;
			updateDropTarget();
		});
	}

	function finishDrag() {
		if (pointerId !== null && captureCard?.hasPointerCapture?.(pointerId)) {
			captureCard.releasePointerCapture(pointerId);
		}
		pointerId = null;
		captureCard = null;
		activeDropTarget = null;
		onStepDragEnd();
	}

	function handleWindowPointerUp(event: PointerEvent) {
		if (event.pointerId !== pointerId) return;
		if (draggedStepKey) {
			suppressClick = true;
			pointerX = event.clientX;
			pointerY = event.clientY;
			updateDropTarget();
			if (activeDropTarget) {
				onDropStep(activeDropTarget.roundIndex, activeDropTarget.stepIndex, activeDropTarget.key);
			}
		}
		finishDrag();
	}

	function cancelDrag() {
		if (pointerId === null) return;
		suppressClick = true;
		finishDrag();
	}
</script>

<svelte:window
	onpointermove={handleWindowPointerMove}
	onpointerup={handleWindowPointerUp}
	onpointercancel={(event) => {
		if (event.pointerId === pointerId) cancelDrag();
	}}
	onblur={cancelDrag}
	onkeydown={(event) => {
		if (event.key === 'Escape') cancelDrag();
	}}
/>

<section class="editor-sorter-panel flex h-full min-h-0 min-w-0 flex-col">
	<div class="pb-2">
		<h3 class="label-title text-xl">Step Sorter</h3>
		<p class="editor-text-muted text-sm">
			Drag slides to change the order or move them between rounds.
		</p>
	</div>

	<div
		bind:this={sorterScroller}
		class="min-h-0 flex-1 overflow-x-hidden overflow-y-auto pb-4 pr-0.5"
	>
		{#each rounds as round, roundIndex}
			<div class="relative mb-5">
				<div class="editor-round-header sticky top-0 z-10 mb-2 rounded-2xl px-3 py-2 shadow-sm">
					<div class="flex min-w-0 flex-wrap items-center justify-between gap-2">
						<div class="min-w-0 flex-1">
							<p class="editor-text truncate text-sm font-bold uppercase tracking-wide">
								{round.title || `Round ${roundIndex + 1}`}
							</p>
						</div>
						<div class="flex min-w-0 flex-wrap items-center justify-end gap-1.5">
							<span class="editor-text-muted text-xs font-semibold">{round.steps.length} steps</span
							>
							<button
								class="theme-surface-muted inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition hover:opacity-85"
								type="button"
								title={`Move ${round.title || `round ${roundIndex + 1}`} up`}
								aria-label={`Move ${round.title || `round ${roundIndex + 1}`} up`}
								onclick={() => moveRound(roundIndex, -1)}
								disabled={roundIndex === 0}
							>
								<iconify-icon icon="fluent:arrow-up-16-filled"></iconify-icon>
							</button>
							<button
								class="theme-surface-muted inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition hover:opacity-85 disabled:opacity-45"
								type="button"
								title={`Move ${round.title || `round ${roundIndex + 1}`} down`}
								aria-label={`Move ${round.title || `round ${roundIndex + 1}`} down`}
								onclick={() => moveRound(roundIndex, 1)}
								disabled={roundIndex === rounds.length - 1}
							>
								<iconify-icon icon="fluent:arrow-down-16-filled"></iconify-icon>
							</button>
							<button
								class="theme-surface-muted inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition hover:opacity-85"
								type="button"
								aria-label={`Edit ${round.title || `round ${roundIndex + 1}`}`}
								title={`Edit ${round.title || `round ${roundIndex + 1}`}`}
								onclick={() => onOpenRoundModal(roundIndex)}
							>
								<iconify-icon icon="fluent:edit-16-filled"></iconify-icon>
							</button>
							<button
								class="editor-danger-icon-button inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border transition hover:opacity-85"
								type="button"
								title={`Delete ${round.title || `round ${roundIndex + 1}`}`}
								aria-label={`Delete ${round.title || `round ${roundIndex + 1}`}`}
								onclick={() => onRemoveRound(roundIndex)}
							>
								<iconify-icon icon="fluent:delete-16-filled"></iconify-icon>
							</button>
						</div>
					</div>
				</div>

				{#if round.steps.length === 0}
					<div
						class={`rounded-2xl border border-dashed p-4 text-sm transition ${
							isDropTargetActive(roundIndex, 0)
								? 'editor-soft-primary'
								: draggedStepKey
									? 'editor-muted-panel'
									: 'editor-muted-panel'
						}`}
						data-empty-round-target
						data-round-index={roundIndex}
					>
						No steps in this round yet. Drop one here or use New Step while this round is selected.
					</div>
				{:else}
					{#each flatSteps.filter((candidate) => candidate.roundIndex === roundIndex) as item, itemIndex (item.stepKey)}
						{@const step = item.step}
						<div class="relative min-w-0" animate:flip={{ duration: 180 }}>
							{#if isDropTargetActive(roundIndex, itemIndex)}
								<div
									class="pointer-events-none absolute inset-x-0 top-0 z-20 h-1 -translate-y-1/2 rounded-full bg-sky-400"
								></div>
							{/if}
							<button
								class={`w-full min-w-0 touch-none select-none rounded-3xl border p-4 text-left shadow-sm transition-colors ${
									draggedStepKey === item.stepKey
										? 'editor-soft-accent opacity-25'
										: selectedStepKey === item.stepKey
											? 'editor-current-step-card shadow-md'
											: 'editor-muted-step-card hover:border-sky-200'
								}`}
								data-step-card
								data-step-key={item.stepKey}
								data-round-index={roundIndex}
								data-step-index={itemIndex}
								onclick={(event) => {
									if (suppressClick && event.detail !== 0) {
										event.preventDefault();
										return;
									}
									onSelectStep(item.stepKey);
								}}
								onpointerdown={(event) => handlePointerDown(event, item.stepKey)}
							>
								<div class="flex items-start justify-between gap-3">
									<div>
										<p class="editor-text-muted text-xs font-bold uppercase tracking-[0.2em]">
											Slide {item.globalIndex + 1}
										</p>
										<h4 class="editor-text mt-1 text-lg font-bold">
											{step.title || 'Untitled step'}
										</h4>
									</div>
									<span class="theme-surface-muted badge">{step.player_input.kind}</span>
								</div>
								<p class="editor-text-muted mt-2 line-clamp-2 text-sm">{stepPreview(step)}</p>
								<div class="mt-3 flex flex-wrap gap-2">
									{#each stepBadges(step) as badge}
										<span class="theme-surface-muted badge">{badge}</span>
									{/each}
								</div>
							</button>
						</div>
					{/each}

					{#if isDropTargetActive(roundIndex, round.steps.length)}
						<div
							class="pointer-events-none absolute inset-x-0 bottom-0 z-20 h-1 translate-y-1/2 rounded-full bg-sky-400"
						></div>
					{/if}
				{/if}
			</div>
		{/each}
	</div>

	{#if draggedItem}
		<div
			aria-hidden="true"
			class="label-title pointer-events-none fixed z-50"
			style={`left: ${dragPointerX - dragOffsetX}px; top: ${dragPointerY - dragOffsetY}px; width: ${dragCardWidth}px;`}
		>
			<div class="editor-soft-accent rounded-3xl border p-4 text-left shadow-2xl backdrop-blur">
				<div class="flex items-start justify-between gap-3">
					<div>
						<p class="editor-text-muted text-xs font-bold uppercase tracking-[0.2em]">
							Slide {draggedItem.globalIndex + 1}
						</p>
						<h4 class="editor-text mt-1 text-lg font-bold">
							{draggedItem.step.title || 'Untitled step'}
						</h4>
					</div>
					<span class="theme-surface-muted badge">{draggedItem.step.player_input.kind}</span>
				</div>
				<p class="editor-text-muted mt-2 line-clamp-2 text-sm">{stepPreview(draggedItem.step)}</p>
				<div class="mt-3 flex flex-wrap gap-2">
					{#each stepBadges(draggedItem.step) as badge}
						<span class="theme-surface-muted badge">{badge}</span>
					{/each}
				</div>
			</div>
		</div>
	{/if}
</section>
