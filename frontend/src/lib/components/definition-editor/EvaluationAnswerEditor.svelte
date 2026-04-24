<script lang="ts">
	import { messages } from '$lib/i18n';
	import OrderingList from '$lib/components/OrderingList.svelte';
	import { getNumberAnswer, getTextAnswer } from './helpers';

	type Props = {
		step: StepDefinition;
		orderedAnswer: string[];
		onSetOrderingAnswerOrder: (step: StepDefinition, values: string[]) => void;
	};

	let { step, orderedAnswer, onSetOrderingAnswerOrder }: Props = $props();
</script>

{#if step.evaluation.type_ === 'ordering_match'}
	<div class="grid gap-3">
		<p class="text-sm font-semibold text-slate-700">{$messages.editor.correctOrderHelp}</p>
		<OrderingList
			items={orderedAnswer}
			variant="editor"
			dragLabel={$messages.editor.dragOrderItem}
			moveUpLabel={$messages.editor.moveOrderItemUp}
			moveDownLabel={$messages.editor.moveOrderItemDown}
			onReorder={(items) => onSetOrderingAnswerOrder(step, items)}
		/>
	</div>
{:else if step.evaluation.type_ === 'exact_number' || step.evaluation.type_ === 'closest_number'}
	<div class="grid gap-3 md:grid-cols-[minmax(0,1fr)_12rem]">
		<label class="input-wrap">
			<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
				{$messages.editor.correctNumber}
			</span>
			<input
				class="input text-lg"
				type="number"
				value={getNumberAnswer(step)}
				oninput={(event) =>
					(step.evaluation.answer = (event.currentTarget as HTMLInputElement).value)}
			/>
		</label>
		<div class="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
			<p class="font-bold text-slate-900">{$messages.editor.scoringSummary}</p>
			<p class="mt-2">
				{step.evaluation.type_ === 'exact_number'
					? $messages.editor.exactNumberSummary
					: $messages.editor.closestNumberSummary}
			</p>
		</div>
	</div>
{:else if step.evaluation.type_ === 'multi_select_weighted'}
	<div class="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
		<p class="font-bold text-slate-900">{$messages.editor.configureScoresAbove}</p>
		<p class="mt-2">{$messages.editor.configurePointsAboveHelp}</p>
	</div>
{:else if step.evaluation.type_ === 'exact_text' && step.player_input.kind === 'radio'}
	<div class="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
		<p class="font-bold text-slate-900">{$messages.editor.markCorrectOption}</p>
		<p class="mt-2">{$messages.editor.markCorrectOptionHelp}</p>
	</div>
{:else if step.evaluation.type_ === 'host_judged'}
	<div class="grid gap-3">
		<div class="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
			<p class="font-bold text-slate-900">{$messages.editor.hostDecidesCorrectness}</p>
			<p class="mt-2">{$messages.editor.hostReviewedHelp}</p>
		</div>
		<label class="input-wrap">
			<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
				{$messages.editor.correctAnswerRubric}
			</span>
			<input
				class="input text-lg"
				value={getTextAnswer(step)}
				placeholder={$messages.editor.expectedAnswerPlaceholder}
				oninput={(event) =>
					(step.evaluation.answer = (event.currentTarget as HTMLInputElement).value)}
			/>
		</label>
	</div>
{:else if step.evaluation.type_ !== 'none'}
	<label class="input-wrap">
		<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
			{$messages.editor.correctAnswerRubric}
		</span>
		<input
			class="input text-lg"
			value={getTextAnswer(step)}
			placeholder={$messages.editor.expectedAnswerPlaceholder}
			oninput={(event) =>
				(step.evaluation.answer = (event.currentTarget as HTMLInputElement).value)}
		/>
	</label>
{:else}
	<div class="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
		<p class="font-bold text-slate-900">{$messages.editor.noAnswerRequired}</p>
		<p class="mt-2">{$messages.editor.displayOnlyHelp}</p>
	</div>
{/if}
