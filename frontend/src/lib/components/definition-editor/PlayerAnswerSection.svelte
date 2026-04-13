<script lang="ts">
	import 'iconify-icon';
	import { messages } from '$lib/i18n';
	import type {
		CheckboxOptionScore,
		EvaluationPresentation,
		InputKindPresentation
	} from './helpers';
	import EditorSectionCard from './EditorSectionCard.svelte';
	import InputKindPicker from './InputKindPicker.svelte';
	import InputOptionsEditor from './InputOptionsEditor.svelte';

	type Props = {
		step: StepDefinition;
		inputKindDetails: Record<PlayerInputKind, InputKindPresentation>;
		inputDetails: InputKindPresentation;
		evaluationDetailsMap: Record<EvaluationType, EvaluationPresentation>;
		checkboxOptionScores: CheckboxOptionScore[];
		onSetPlayerInputKind: (step: StepDefinition, kind: PlayerInputKind) => void;
		onAddInputOption: (step: StepDefinition) => void;
		onRemoveInputOption: (step: StepDefinition, optionIndex: number) => void;
		onSetInputOptionValue: (step: StepDefinition, optionIndex: number, value: string) => void;
		onSetRadioCorrectOption: (step: StepDefinition, option: string) => void;
		onSetCheckboxOptionPoints: (step: StepDefinition, optionIndex: number, points: number) => void;
	};

	let {
		step,
		inputKindDetails,
		inputDetails,
		evaluationDetailsMap,
		checkboxOptionScores,
		onSetPlayerInputKind,
		onAddInputOption,
		onRemoveInputOption,
		onSetInputOptionValue,
		onSetRadioCorrectOption,
		onSetCheckboxOptionPoints
	}: Props = $props();
</script>

<EditorSectionCard
	id="player-answer"
	icon="fluent:people-community-16-filled"
	iconClass="bg-emerald-100 text-emerald-700"
	title={$messages.editor.howPlayersAnswer}
	description={$messages.editor.howPlayersAnswerHelp}
>
	<InputKindPicker
		selectedKind={step.player_input.kind}
		{inputKindDetails}
		onSelect={(kind) => onSetPlayerInputKind(step, kind)}
	/>

	<div class="mt-5 rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-4">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div>
				<p class="text-lg font-bold text-slate-900">{inputDetails.label}</p>
				<p class="text-sm text-slate-600">{inputDetails.description}</p>
			</div>
			<span
				class="inline-flex items-center gap-2 rounded-full bg-white px-3 py-2 text-xs font-bold uppercase tracking-[0.16em] text-slate-500"
			>
				<iconify-icon icon={inputDetails.icon}></iconify-icon>
				{$messages.editor.recommendedScoring}:
				{evaluationDetailsMap[inputDetails.recommendedEvaluation].label}
			</span>
		</div>

		<div class="mt-4 grid gap-4">
			{#if inputDetails.usesPrompt || inputDetails.usesPlaceholder}
				<div class="grid gap-4 md:grid-cols-2">
					{#if inputDetails.usesPrompt}
						<label class="input-wrap">
							<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
								{$messages.editor.inputPrompt}
							</span>
							<input
								bind:value={step.player_input.prompt}
								class="input text-lg"
								placeholder={$messages.editor.inputPromptPlaceholder}
							/>
						</label>
					{/if}
					{#if inputDetails.usesPlaceholder}
						<label class="input-wrap">
							<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
								{$messages.editor.placeholder}
							</span>
							<input
								bind:value={step.player_input.placeholder}
								class="input text-lg"
								placeholder={$messages.editor.placeholderHelp}
							/>
						</label>
					{/if}
				</div>
			{/if}

			{#if inputDetails.usesNumericRange}
				<div class="grid gap-3 md:grid-cols-3">
					<label class="input-wrap">
						<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
							{$messages.editor.minValue}
						</span>
						<input bind:value={step.player_input.min_value} type="number" class="input text-lg" />
					</label>
					<label class="input-wrap">
						<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
							{$messages.editor.maxValue}
						</span>
						<input bind:value={step.player_input.max_value} type="number" class="input text-lg" />
					</label>
					<label class="input-wrap">
						<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
							{$messages.editor.sliderStep}
						</span>
						<input
							bind:value={step.player_input.step}
							type="number"
							min="0"
							class="input text-lg"
						/>
					</label>
				</div>
			{/if}

			{#if inputDetails.usesOptions}
				<InputOptionsEditor
					{step}
					{checkboxOptionScores}
					{onAddInputOption}
					{onRemoveInputOption}
					{onSetInputOptionValue}
					{onSetRadioCorrectOption}
					{onSetCheckboxOptionPoints}
				/>
			{/if}
		</div>
	</div>
</EditorSectionCard>
