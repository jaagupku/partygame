<script lang="ts">
	import { messages } from '$lib/i18n';
	import type { EvaluationPresentation } from './helpers';
	import EditorSectionCard from './EditorSectionCard.svelte';
	import EvaluationAnswerEditor from './EvaluationAnswerEditor.svelte';
	import EvaluationPicker from './EvaluationPicker.svelte';

	type Props = {
		step: StepDefinition;
		availableEvaluationDetails: EvaluationPresentation[];
		evaluationDetails: EvaluationPresentation;
		orderedAnswer: string[];
		onSetEvaluationType: (step: StepDefinition, evaluationType: EvaluationType) => void;
		onSetOrderingAnswerOrder: (step: StepDefinition, values: string[]) => void;
	};

	let {
		step,
		availableEvaluationDetails,
		evaluationDetails,
		orderedAnswer,
		onSetEvaluationType,
		onSetOrderingAnswerOrder
	}: Props = $props();
</script>

<EditorSectionCard
	id="scoring"
	icon="fluent:checkmark-circle-16-filled"
	iconClass="bg-amber-100 text-amber-700"
	title={$messages.editor.scoringAndCorrectAnswer}
	description={$messages.editor.scoringHelp}
>
	<EvaluationPicker
		selectedType={step.evaluation.type_}
		{availableEvaluationDetails}
		onSelect={(type) => onSetEvaluationType(step, type)}
	/>

	<div class="editor-nested-panel mt-5 rounded-[1.5rem] border p-4">
		<div class="flex flex-wrap items-center justify-between gap-4">
			<div>
				<p class="editor-text text-lg font-bold">{evaluationDetails.label}</p>
				<p class="editor-text-muted text-sm">{evaluationDetails.description}</p>
			</div>
			{#if step.evaluation.type_ !== 'multi_select_weighted' && step.evaluation.type_ !== 'map_distance' && step.evaluation.type_ !== 'none'}
				<label class="input-wrap min-w-32">
					<span class="editor-text-muted text-xs font-bold uppercase tracking-wide">
						{$messages.editor.points}
					</span>
					<input bind:value={step.evaluation.points} type="number" class="input text-lg" />
				</label>
			{/if}
		</div>

		<div class="mt-4">
			<EvaluationAnswerEditor {step} {orderedAnswer} {onSetOrderingAnswerOrder} />
		</div>
	</div>
</EditorSectionCard>
