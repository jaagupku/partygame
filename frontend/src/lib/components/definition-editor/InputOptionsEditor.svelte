<script lang="ts">
	import { messages } from '$lib/i18n';
	import { getRadioCorrectOption, type CheckboxOptionScore } from './helpers';

	type Props = {
		step: StepDefinition;
		checkboxOptionScores: CheckboxOptionScore[];
		onAddInputOption: (step: StepDefinition) => void;
		onRemoveInputOption: (step: StepDefinition, optionIndex: number) => void;
		onSetInputOptionValue: (step: StepDefinition, optionIndex: number, value: string) => void;
		onSetRadioCorrectOption: (step: StepDefinition, option: string) => void;
		onSetCheckboxOptionPoints: (step: StepDefinition, optionIndex: number, points: number) => void;
	};

	let {
		step,
		checkboxOptionScores,
		onAddInputOption,
		onRemoveInputOption,
		onSetInputOptionValue,
		onSetRadioCorrectOption,
		onSetCheckboxOptionPoints
	}: Props = $props();
</script>

<div class="editor-nested-panel rounded-[1.5rem] border p-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div>
			<p class="editor-text text-lg font-bold">
				{step.player_input.kind === 'ordering'
					? $messages.editor.itemsToOrder
					: step.player_input.kind === 'radio'
						? $messages.editor.answerChoices
						: $messages.editor.selectableAnswers}
			</p>
			<p class="editor-text-muted text-sm">
				{step.player_input.kind === 'ordering'
					? $messages.editor.itemsToOrderHelp
					: $messages.editor.selectableAnswersHelp}
			</p>
		</div>
		<button class="btn btn-ghost text-sm" type="button" onclick={() => onAddInputOption(step)}>
			{$messages.editor.addOption}
		</button>
	</div>

	<div class="mt-4 grid gap-3">
		{#each step.player_input.options as option, optionIndex}
			<div
				class="editor-muted-panel grid gap-3 rounded-2xl border p-3 md:grid-cols-[auto_1fr_auto_auto]"
			>
				<div
					class="theme-surface inline-flex h-11 w-11 items-center justify-center rounded-2xl text-sm font-bold"
				>
					{optionIndex + 1}
				</div>
				<input
					value={option}
					class="input text-lg"
					oninput={(event) =>
						onSetInputOptionValue(
							step,
							optionIndex,
							(event.currentTarget as HTMLInputElement).value
						)}
				/>
				{#if step.player_input.kind === 'radio' && step.evaluation.type_ === 'exact_text'}
					<label
						class="theme-surface flex items-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold"
					>
						<input
							type="radio"
							name={`radio-correct-${step.id}`}
							checked={getRadioCorrectOption(step) === step.player_input.options[optionIndex]}
							onchange={() =>
								onSetRadioCorrectOption(step, step.player_input.options[optionIndex] ?? '')}
						/>
						{$messages.editor.correct}
					</label>
				{:else if step.player_input.kind === 'checkbox' && step.evaluation.type_ === 'multi_select_weighted'}
					<label class="input-wrap">
						<span class="editor-text-muted text-xs font-bold uppercase tracking-wide">
							{$messages.editor.points}
						</span>
						<input
							class="input w-24 text-lg"
							type="number"
							value={checkboxOptionScores[optionIndex]?.points ?? 0}
							oninput={(event) =>
								onSetCheckboxOptionPoints(
									step,
									optionIndex,
									Number((event.currentTarget as HTMLInputElement).value || 0)
								)}
						/>
					</label>
				{:else}
					<div></div>
				{/if}
				<button
					class="btn btn-danger text-sm"
					type="button"
					onclick={() => onRemoveInputOption(step, optionIndex)}
				>
					{$messages.editor.removeOption}
				</button>
			</div>
		{/each}
	</div>
</div>
