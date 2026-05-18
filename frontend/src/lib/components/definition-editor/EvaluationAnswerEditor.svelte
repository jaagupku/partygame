<script lang="ts">
	import { messages } from '$lib/i18n';
	import OrderingList from '$lib/components/OrderingList.svelte';
	import {
		getExactTextMaxDistance,
		getNumberAnswer,
		getTextAnswer,
		getTextAnswers
	} from './helpers';

	type Props = {
		step: StepDefinition;
		orderedAnswer: string[];
		onSetOrderingAnswerOrder: (step: StepDefinition, values: string[]) => void;
	};

	let { step, orderedAnswer, onSetOrderingAnswerOrder }: Props = $props();

	const textAnswers = $derived(getTextAnswers(step));

	function setTextAnswer(index: number, value: string) {
		const answers = [...textAnswers];
		answers[index] = value;
		step.evaluation.answer = answers;
	}

	function addTextAnswer() {
		step.evaluation.answer = [...textAnswers, ''];
	}

	function removeTextAnswer(index: number) {
		const answers = textAnswers.filter((_, answerIndex) => answerIndex !== index);
		step.evaluation.answer = answers.length > 0 ? answers : [''];
	}
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
{:else if step.evaluation.type_ === 'exact_text' && step.player_input.kind === 'text'}
	<div class="grid gap-3">
		<div class="grid gap-3">
			<div class="flex items-center justify-between gap-3">
				<p class="text-sm font-bold uppercase tracking-wide text-slate-500">
					{$messages.editor.acceptedAnswers}
				</p>
				<button type="button" class="btn btn-ghost text-sm" onclick={addTextAnswer}>
					{$messages.editor.addAcceptedAnswer}
				</button>
			</div>
			{#each textAnswers as answer, index}
				<div class="grid gap-2 md:grid-cols-[minmax(0,1fr)_8rem]">
					<input
						class="input text-lg"
						value={answer}
						placeholder={$messages.editor.expectedAnswerPlaceholder}
						oninput={(event) =>
							setTextAnswer(index, (event.currentTarget as HTMLInputElement).value)}
					/>
					<button
						type="button"
						class="btn btn-ghost text-sm"
						disabled={textAnswers.length <= 1}
						onclick={() => removeTextAnswer(index)}
					>
						{$messages.editor.removeAcceptedAnswer}
					</button>
				</div>
			{/each}
		</div>
		<label class="input-wrap md:max-w-xs">
			<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
				{$messages.editor.typoTolerance}
			</span>
			<input
				class="input text-lg"
				type="number"
				min="0"
				step="1"
				value={getExactTextMaxDistance(step)}
				oninput={(event) =>
					(step.evaluation.max_distance = Math.max(
						0,
						Math.trunc(Number((event.currentTarget as HTMLInputElement).value) || 0)
					))}
			/>
			<span class="text-sm text-slate-600">{$messages.editor.typoToleranceHelp}</span>
		</label>
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
