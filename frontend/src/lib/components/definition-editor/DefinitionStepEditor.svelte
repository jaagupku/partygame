<script lang="ts">
	import { messages } from '$lib/i18n';
	import {
		getEvaluationDetails,
		getInputKindDetails,
		getCheckboxOptionScores,
		getEvaluationDetailsForInputKind,
		getOrderingAnswer,
		getStepHealthIssues
	} from './helpers';
	import MainScreenSection from './MainScreenSection.svelte';
	import PlayerAnswerSection from './PlayerAnswerSection.svelte';
	import ScoringSection from './ScoringSection.svelte';
	import SectionNav from './SectionNav.svelte';
	import SettingsSection from './SettingsSection.svelte';
	import StepHeader from './StepHeader.svelte';
	import type { FlatStepItem, StepHeaderAction } from './types';

	type Props = {
		selectedStep: StepDefinition;
		selectedFlatStep: FlatStepItem;
		selectedStepPosition: number;
		totalSteps: number;
		showAdvancedFields: boolean;
		uploadKey: string | null;
		onToggleAdvancedFields: () => void;
		onSelectStep: (stepKey: string | undefined) => void;
		onAddStepAfter: () => void;
		onRemoveSelectedStep: () => void;
		onPreview: () => void;
		onOpenShortcutHelp: () => void;
		onSetPlayerInputKind: (step: StepDefinition, kind: PlayerInputKind) => void;
		onSetEvaluationType: (step: StepDefinition, evaluationType: EvaluationType) => void;
		onAddInputOption: (step: StepDefinition) => void;
		onRemoveInputOption: (step: StepDefinition, optionIndex: number) => void;
		onSetInputOptionValue: (step: StepDefinition, optionIndex: number, value: string) => void;
		onSetOrderingAnswerOrder: (step: StepDefinition, values: string[]) => void;
		onSetRadioCorrectOption: (step: StepDefinition, option: string) => void;
		onSetCheckboxOptionPoints: (step: StepDefinition, optionIndex: number, points: number) => void;
		onAddMedia: (step: StepDefinition) => void;
		onRemoveMedia: (step: StepDefinition) => void;
		onUpdateMediaType: (step: StepDefinition, mediaType: 'image' | 'audio' | 'video') => void;
		onUploadMedia: (event: Event, step: StepDefinition, stepId: string) => void;
		flatSteps: FlatStepItem[];
	};

	let {
		selectedStep,
		selectedFlatStep,
		selectedStepPosition,
		totalSteps,
		showAdvancedFields,
		uploadKey,
		onToggleAdvancedFields,
		onSelectStep,
		onAddStepAfter,
		onRemoveSelectedStep,
		onPreview,
		onOpenShortcutHelp,
		onSetPlayerInputKind,
		onSetEvaluationType,
		onAddInputOption,
		onRemoveInputOption,
		onSetInputOptionValue,
		onSetOrderingAnswerOrder,
		onSetRadioCorrectOption,
		onSetCheckboxOptionPoints,
		onAddMedia,
		onRemoveMedia,
		onUpdateMediaType,
		onUploadMedia,
		flatSteps
	}: Props = $props();

	const inputKindDetails = $derived(getInputKindDetails());
	const evaluationDetailsMap = $derived(getEvaluationDetails());
	const inputDetails = $derived(inputKindDetails[selectedStep.player_input.kind]);
	const availableEvaluationDetails = $derived(
		getEvaluationDetailsForInputKind(selectedStep.player_input.kind)
	);
	const evaluationDetails = $derived(evaluationDetailsMap[selectedStep.evaluation.type_]);
	const checkboxOptionScores = $derived(getCheckboxOptionScores(selectedStep));
	const healthIssues = $derived(getStepHealthIssues(selectedStep));
	const orderedAnswer = $derived(getOrderingAnswer(selectedStep));
	const sectionNav = $derived($messages.editor.sectionNavigation);

	const headerActions = $derived<StepHeaderAction[]>([
		{
			label: showAdvancedFields ? $messages.editor.hideAdvanced : $messages.editor.showAdvanced,
			shortcut: 'Cmd/Ctrl + ,',
			icon: 'fluent:settings-16-filled',
			onClick: onToggleAdvancedFields
		},
		{
			label: $messages.editor.headerActionLabels.previousStep,
			shortcut: 'Alt + ArrowUp',
			icon: 'fluent:chevron-left-16-filled',
			onClick: () => onSelectStep(flatSteps[selectedStepPosition - 1]?.stepKey),
			disabled: selectedStepPosition <= 0
		},
		{
			label: $messages.editor.headerActionLabels.nextStep,
			shortcut: 'Alt + ArrowDown',
			icon: 'fluent:chevron-right-16-filled',
			onClick: () => onSelectStep(flatSteps[selectedStepPosition + 1]?.stepKey),
			disabled: selectedStepPosition < 0 || selectedStepPosition >= totalSteps - 1
		},
		{
			label: $messages.common.preview,
			shortcut: 'Cmd/Ctrl + Shift + P',
			icon: 'fluent:desktop-16-filled',
			onClick: onPreview
		},
		{
			label: $messages.editor.headerActionLabels.deleteStep,
			shortcut: 'Cmd/Ctrl + Backspace/Delete',
			icon: 'fluent:delete-16-filled',
			onClick: onRemoveSelectedStep,
			variant: 'danger'
		},
		{
			label: $messages.editor.headerActionLabels.shortcuts,
			shortcut: '?',
			icon: 'fluent:question-circle-16-filled',
			onClick: onOpenShortcutHelp
		}
	]);
</script>

<section class="flex h-full min-h-0 flex-col bg-white/70">
	<StepHeader
		{selectedFlatStep}
		selectedStepTitle={selectedStep.title || $messages.editor.untitledStep}
		{headerActions}
		{healthIssues}
		{onAddStepAfter}
	/>

	<div class="min-h-0 flex-1 overflow-y-auto px-4 pb-4 pr-3">
		<SectionNav sections={sectionNav} />

		<div class="grid gap-5">
			<MainScreenSection
				step={selectedStep}
				{showAdvancedFields}
				{uploadKey}
				{onAddMedia}
				{onRemoveMedia}
				{onUpdateMediaType}
				{onUploadMedia}
			/>

			<PlayerAnswerSection
				step={selectedStep}
				{inputKindDetails}
				{inputDetails}
				{evaluationDetailsMap}
				{checkboxOptionScores}
				{onSetPlayerInputKind}
				{onAddInputOption}
				{onRemoveInputOption}
				{onSetInputOptionValue}
				{onSetRadioCorrectOption}
				{onSetCheckboxOptionPoints}
			/>

			<ScoringSection
				step={selectedStep}
				{availableEvaluationDetails}
				{evaluationDetails}
				{orderedAnswer}
				{onSetEvaluationType}
				{onSetOrderingAnswerOrder}
			/>

			<SettingsSection step={selectedStep} />
		</div>
	</div>
</section>
