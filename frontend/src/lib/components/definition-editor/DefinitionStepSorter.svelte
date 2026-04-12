<script lang="ts">
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
		onRemoveRound: (roundIndex: number) => void;
		onStepDragStart: (event: PointerEvent, stepKey: string) => void;
		onStepDragMove: (event: PointerEvent) => void;
		onStepDragEnd: () => void;
		onActivateDropTarget: (key: string, targetRoundIndex: number, targetStepIndex: number) => void;
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

	function updateAutoScroll(pointerY: number) {
		if (!sorterScroller || !draggedStepKey) {
			return;
		}
		const rect = sorterScroller.getBoundingClientRect();
		const edgeThreshold = 72;
		const maxStep = 18;
		if (pointerY < rect.top + edgeThreshold) {
			const distance = rect.top + edgeThreshold - pointerY;
			sorterScroller.scrollTop -= Math.min(maxStep, Math.max(4, distance / 4));
			return;
		}
		if (pointerY > rect.bottom - edgeThreshold) {
			const distance = pointerY - (rect.bottom - edgeThreshold);
			sorterScroller.scrollTop += Math.min(maxStep, Math.max(4, distance / 4));
		}
	}

	function handleWindowPointerMove(event: PointerEvent) {
		onStepDragMove(event);
		if (!draggedStepKey) {
			return;
		}
		updateAutoScroll(event.clientY);
		const target = parseDropTarget(
			document.elementFromPoint(event.clientX, event.clientY) as HTMLElement | null,
			event.clientY
		);
		if (!target) {
			return;
		}
		activeDropTarget = target;
		onActivateDropTarget(target.key, target.roundIndex, target.stepIndex);
	}

	function handleWindowPointerUp() {
		if (draggedStepKey && activeDropTarget) {
			onDropStep(activeDropTarget.roundIndex, activeDropTarget.stepIndex, activeDropTarget.key);
		}
		activeDropTarget = null;
		onStepDragEnd();
	}
</script>

<svelte:window onpointermove={handleWindowPointerMove} onpointerup={handleWindowPointerUp} />

<section class="flex h-full min-h-0 flex-col rounded-3xl border border-slate-200 bg-white/65 p-4">
	<div>
		<h3 class="label-title text-xl">Step Sorter</h3>
		<p class="text-sm text-slate-600">
			Drag slides to change the order or move them between rounds.
		</p>
	</div>

	<div
		bind:this={sorterScroller}
		class="mt-4 min-h-0 flex-1 overflow-x-hidden overflow-y-auto pr-1"
	>
		{#each rounds as round, roundIndex}
			<div class="mb-5">
				<div class="sticky top-0 z-10 mb-2 rounded-2xl bg-sky-50 px-3 py-2 shadow-sm">
					<div class="flex items-center justify-between gap-2">
						<div>
							<p class="text-sm font-bold uppercase tracking-wide text-sky-800">
								{round.title || `Round ${roundIndex + 1}`}
							</p>
						</div>
						<div class="flex items-center gap-2">
							<span class="text-xs font-semibold text-sky-700">{round.steps.length} steps</span>
							<button
								class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-sky-200 bg-white text-sky-700 transition hover:bg-sky-100"
								type="button"
								aria-label={`Edit ${round.title || `round ${roundIndex + 1}`}`}
								onclick={() => onOpenRoundModal(roundIndex)}
							>
								<iconify-icon icon="fluent:edit-16-filled"></iconify-icon>
							</button>
							<button
								class="btn btn-danger px-3 py-2 text-xs"
								type="button"
								onclick={() => onRemoveRound(roundIndex)}
							>
								Remove
							</button>
						</div>
					</div>
				</div>

				{#if round.steps.length === 0}
					<div
						class={`rounded-2xl border border-dashed p-4 text-sm transition ${
							isDropTargetActive(roundIndex, 0)
								? 'border-sky-400 bg-sky-100 text-sky-800'
								: draggedStepKey
									? 'border-sky-200 bg-sky-50/80 text-slate-500'
									: 'border-slate-300 bg-slate-50/80 text-slate-500'
						}`}
						data-empty-round-target
						data-round-index={roundIndex}
					>
						No steps in this round yet. Drop one here or use New Step while this round is selected.
					</div>
				{:else}
					{#each flatSteps.filter((candidate) => candidate.roundIndex === roundIndex) as item, itemIndex (item.stepKey)}
						{@const step = item.step}
						<div class="min-w-0" animate:flip={{ duration: 180, easing: (t) => t }}>
							{#if isDropTargetActive(roundIndex, itemIndex)}
								<div
									class="mb-1 h-2 rounded-full border-2 border-dashed border-sky-400 bg-sky-100"
								></div>
							{/if}
							<button
								class={`w-full min-w-0 rounded-3xl border p-4 text-left shadow-sm transition ${
									selectedStepKey === item.stepKey
										? 'border-sky-400 bg-sky-50 shadow-md'
										: draggedStepKey === item.stepKey
											? 'pointer-events-none border-orange-300 bg-orange-50 opacity-0'
											: 'border-slate-200 bg-white/90 hover:border-sky-200'
								}`}
								data-step-card
								data-round-index={roundIndex}
								data-step-index={itemIndex}
								onclick={() => onSelectStep(item.stepKey)}
								onpointerdown={(event) => onStepDragStart(event, item.stepKey)}
							>
								<div class="flex items-start justify-between gap-3">
									<div>
										<p class="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">
											Slide {item.globalIndex + 1}
										</p>
										<h4 class="mt-1 text-lg font-bold text-slate-900">
											{step.title || 'Untitled step'}
										</h4>
									</div>
									<span class="badge bg-slate-100 text-slate-700">{step.player_input.kind}</span>
								</div>
								<p class="mt-2 line-clamp-2 text-sm text-slate-600">{stepPreview(step)}</p>
								<div class="mt-3 flex flex-wrap gap-2">
									{#each stepBadges(step) as badge}
										<span class="badge bg-white text-slate-700">{badge}</span>
									{/each}
								</div>
							</button>
						</div>
					{/each}

					{#if isDropTargetActive(roundIndex, round.steps.length)}
						<div
							class="mb-1 h-2 rounded-full border-2 border-dashed border-sky-400 bg-sky-100"
						></div>
					{/if}
				{/if}
			</div>
		{/each}
	</div>

	{#if draggedItem}
		<div
			class="pointer-events-none fixed z-50 w-[min(20rem,calc(100vw-2rem))]"
			style={`left: ${Math.max(12, dragPointerX - dragOffsetX)}px; top: ${Math.max(
				12,
				dragPointerY - dragOffsetY
			)}px; width: ${Math.max(220, dragCardWidth)}px;`}
		>
			<div
				class="rounded-3xl border border-orange-300 bg-white/95 p-4 text-left shadow-2xl ring-2 ring-orange-200 backdrop-blur"
			>
				<div class="flex items-start justify-between gap-3">
					<div>
						<p class="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">
							Slide {draggedItem.globalIndex + 1}
						</p>
						<h4 class="mt-1 text-lg font-bold text-slate-900">
							{draggedItem.step.title || 'Untitled step'}
						</h4>
					</div>
					<span class="badge bg-slate-100 text-slate-700">{draggedItem.step.player_input.kind}</span
					>
				</div>
				<p class="mt-2 line-clamp-2 text-sm text-slate-600">{stepPreview(draggedItem.step)}</p>
				<div class="mt-3 flex flex-wrap gap-2">
					{#each stepBadges(draggedItem.step) as badge}
						<span class="badge bg-white text-slate-700">{badge}</span>
					{/each}
				</div>
			</div>
		</div>
	{/if}
</section>
