<script lang="ts">
	import { messages } from '$lib/i18n';
	import { getNumberAnswer, getTextAnswer } from './helpers';

	type Props = {
		step: StepDefinition;
		orderedAnswer: string[];
		onSetOrderingAnswer: (step: StepDefinition, optionIndex: number, value: string) => void;
	};

	let { step, orderedAnswer, onSetOrderingAnswer }: Props = $props();
</script>

{#if step.evaluation.type_ === 'ordering_match'}
	<div class="grid gap-3">
		<p class="text-sm font-semibold text-slate-700">{$messages.editor.correctOrderHelp}</p>
		{#each orderedAnswer as answerValue, optionIndex}
			<label
				class="grid gap-3 rounded-2xl border border-slate-200 bg-white p-3 md:grid-cols-[auto_1fr]"
			>
				<div
					class="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-amber-50 text-sm font-bold text-amber-700"
				>
					{optionIndex + 1}
				</div>
				<input
					value={answerValue}
					class="input text-lg"
					oninput={(event) =>
						onSetOrderingAnswer(step, optionIndex, (event.currentTarget as HTMLInputElement).value)}
				/>
			</label>
		{/each}
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
	<div class="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
		<p class="font-bold text-slate-900">{$messages.editor.hostDecidesCorrectness}</p>
		<p class="mt-2">{$messages.editor.hostReviewedHelp}</p>
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
