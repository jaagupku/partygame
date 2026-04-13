<script lang="ts">
	import 'iconify-icon';
	import { messages } from '$lib/i18n';
	import type { StepHealthIssue } from './helpers';
	import type { FlatStepItem, StepHeaderAction } from './types';

	type Props = {
		selectedFlatStep: FlatStepItem;
		selectedStepTitle: string;
		headerActions: StepHeaderAction[];
		healthIssues: StepHealthIssue[];
		onAddStepAfter: () => void;
	};

	let { selectedFlatStep, selectedStepTitle, headerActions, healthIssues, onAddStepAfter }: Props =
		$props();

	function getTooltipText(action: StepHeaderAction) {
		return action.shortcut ? `${action.label} — ${action.shortcut}` : action.label;
	}
</script>

<div class="flex flex-wrap items-start justify-between gap-3 px-4 py-3">
	<div>
		<p class="text-sm font-bold uppercase tracking-wide text-slate-500">
			{selectedFlatStep.roundTitle} · {$messages.editor.slide}
			{selectedFlatStep.globalIndex + 1}
		</p>
		<h2 class="label-title text-2xl">{selectedStepTitle}</h2>
	</div>
	<div class="flex flex-wrap items-center gap-2">
		{#each headerActions as action}
			<button
				class={`inline-flex h-11 w-11 items-center justify-center rounded-full border text-lg transition ${
					action.variant === 'danger'
						? 'border-red-200 bg-red-50 text-red-700 hover:bg-red-100 disabled:border-red-100 disabled:bg-red-50/60 disabled:text-red-300'
						: 'border-slate-200 bg-white text-slate-700 hover:bg-slate-100 disabled:border-slate-100 disabled:bg-slate-50 disabled:text-slate-300'
				}`}
				type="button"
				aria-label={getTooltipText(action)}
				title={getTooltipText(action)}
				onclick={action.onClick}
				disabled={action.disabled}
			>
				<iconify-icon icon={action.icon}></iconify-icon>
			</button>
		{/each}
		<button
			class="btn btn-accent inline-flex items-center gap-2 px-4 py-2 text-sm"
			type="button"
			onclick={onAddStepAfter}
			title={`${$messages.editor.headerActionLabels.addStepAfter} — Cmd/Ctrl + Shift + A`}
		>
			<iconify-icon icon="fluent:add-16-filled"></iconify-icon>
			{$messages.editor.headerActionLabels.addStepAfter}
		</button>
	</div>
</div>

{#if healthIssues.length > 0}
	<div class="flex flex-wrap gap-2 px-4 pb-2">
		{#each healthIssues as issue}
			<span
				class="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold uppercase tracking-[0.16em] text-amber-800"
			>
				<iconify-icon icon={issue.icon}></iconify-icon>
				{issue.label}
			</span>
		{/each}
	</div>
{/if}
