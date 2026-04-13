<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import DefinitionConfirmModal from './DefinitionConfirmModal.svelte';
	import DefinitionDetailsModal from './DefinitionDetailsModal.svelte';
	import DefinitionEditorToolbar from './DefinitionEditorToolbar.svelte';
	import DefinitionPreviewModal from './DefinitionPreviewModal.svelte';
	import DefinitionRoundModal from './DefinitionRoundModal.svelte';
	import DefinitionShortcutHelpModal from './DefinitionShortcutHelpModal.svelte';
	import DefinitionStepEditor from './DefinitionStepEditor.svelte';
	import DefinitionStepSorter from './DefinitionStepSorter.svelte';
	import DefinitionStepTemplateModal from './DefinitionStepTemplateModal.svelte';
	import { messages } from '$lib/i18n';
	import {
		DEFAULT_EVALUATION_BY_INPUT_KIND,
		MEDIA_TYPES,
		INPUT_KIND_EVALUATIONS,
		buildCheckboxWeightedAnswer,
		buildFlatSteps,
		buildRuntimePreviewStep,
		createStepFromTemplate,
		getStepTemplates,
		getCheckboxOptionScores,
		isCheckboxWeightedAnswer,
		normalizeAnswer
	} from './helpers';

	interface DefinitionEditorProps {
		definitionId?: string;
	}

	const stepKeys = new WeakMap<StepDefinition, string>();
	let stepKeyCounter = 0;

	let { definitionId }: DefinitionEditorProps = $props();

	let draft = $state<GameDefinition>(createEmptyDefinition());
	let persistedDefinitionId = $state('');
	let selectedStepKey = $state<string | null>(null);
	let loadingEditor = $state(false);
	let saving = $state(false);
	let statusMessage = $state('');
	let errorMessage = $state('');
	let uploadKey = $state<string | null>(null);
	let uploadError = $state('');
	let isNewDefinition = $state(true);
	let pendingDragKey = $state<string | null>(null);
	let draggedStepKey = $state<string | null>(null);
	let dropTargetKey = $state<string | null>(null);
	let dragPreviewDefinition = $state<GameDefinition | null>(null);
	let dragPointer = $state({ x: 0, y: 0 });
	let dragPointerOffset = $state({ x: 0, y: 0 });
	let dragStartPointer = $state({ x: 0, y: 0 });
	let dragCardWidth = $state(320);
	let editingRoundIndex = $state<number | null>(null);
	let roundModalTitle = $state('');
	let roundModalId = $state('');
	let showAdvancedFields = $state(false);
	let showRoundAdvancedFields = $state(false);
	let showPreviewModal = $state(false);
	let showShortcutHelpModal = $state(false);
	let showDefinitionDetailsModal = $state(false);
	let showStepTemplateModal = $state(false);
	let definitionDescriptionDraft = $state('');
	let definitionIdDraft = $state('');
	let showDefinitionAdvancedFields = $state(false);
	let editingTitle = $state(false);
	let pendingStepInsert = $state<{ roundIndex: number; stepIndex: number } | null>(null);
	let pendingDelete = $state<
		| {
				type: 'round';
				roundIndex: number;
				title: string;
				message: string;
				confirmLabel: string;
		  }
		| {
				type: 'step';
				title: string;
				message: string;
				confirmLabel: string;
		  }
		| null
	>(null);

	const displayDefinition = $derived(dragPreviewDefinition ?? draft);
	const flatSteps = $derived(buildFlatSteps(displayDefinition, getStepKey));
	const selectedFlatStep = $derived(
		selectedStepKey ? (flatSteps.find((item) => item.stepKey === selectedStepKey) ?? null) : null
	);
	const selectedStep = $derived(selectedFlatStep?.step ?? null);
	const selectedRoundIndex = $derived(
		selectedFlatStep?.roundIndex ?? (draft.rounds.length > 0 ? 0 : -1)
	);
	const selectedStepPosition = $derived(
		selectedFlatStep ? flatSteps.findIndex((item) => item.stepKey === selectedFlatStep.stepKey) : -1
	);
	const draggedFlatStep = $derived(
		draggedStepKey ? (flatSteps.find((item) => item.stepKey === draggedStepKey) ?? null) : null
	);
	const previewStep = $derived(selectedStep ? buildRuntimePreviewStep(selectedStep) : undefined);
	const previewCountdown = $derived(selectedStep?.timer.seconds ?? 0);
	const breadcrumbCurrentLabel = $derived(
		isNewDefinition
			? $messages.definitions.newDefinitionBreadcrumb
			: $messages.definitions.editDefinitionBreadcrumb
	);
	const shortcutGroups = $derived($messages.editor.shortcutGroups);

	onMount(async () => {
		await loadEditor();
	});

	$effect(() => {
		if (flatSteps.length === 0) {
			selectedStepKey = null;
			return;
		}
		if (!selectedStepKey || !flatSteps.some((item) => item.stepKey === selectedStepKey)) {
			selectedStepKey = flatSteps[0].stepKey;
		}
	});

	async function loadEditor() {
		if (!definitionId) {
			isNewDefinition = true;
			persistedDefinitionId = '';
			draft = createEmptyDefinition();
			selectedStepKey = buildFlatSteps(draft, getStepKey)[0]?.stepKey ?? null;
			return;
		}
		isNewDefinition = false;
		persistedDefinitionId = definitionId;
		loadingEditor = true;
		errorMessage = '';
		statusMessage = '';
		const response = await fetch(`/api/v1/definitions/${definitionId}`);
		loadingEditor = false;
		if (!response.ok) {
			errorMessage = $messages.definitions.couldNotLoadDefinition(definitionId);
			return;
		}
		draft = structuredClone(await response.json());
		selectedStepKey = buildFlatSteps(draft, getStepKey)[0]?.stepKey ?? null;
	}

	function getStepKey(step: StepDefinition): string {
		let key = stepKeys.get(step);
		if (!key) {
			stepKeyCounter += 1;
			key = `step-key-${stepKeyCounter}`;
			stepKeys.set(step, key);
		}
		return key;
	}

	function createEmptyDefinition(): GameDefinition {
		return {
			id: '',
			title: $messages.definitions.untitledDefinition,
			description: '',
			rounds: [createEmptyRound(1, true)]
		};
	}

	function createEmptyRound(index: number, withInitialStep = false): RoundDefinition {
		return {
			id: `round_${index}`,
			title: `${$messages.editor.roundName} ${index}`,
			steps: withInitialStep ? [createStepFromTemplate(index, 1, 'blank')] : []
		};
	}

	function selectStep(stepKey: string | undefined) {
		selectedStepKey = stepKey ?? null;
	}

	function openPreview() {
		showPreviewModal = true;
	}

	function closePreview() {
		showPreviewModal = false;
	}

	function openShortcutHelp() {
		showShortcutHelpModal = true;
	}

	function closeShortcutHelp() {
		showShortcutHelpModal = false;
	}

	function beginTitleEdit() {
		editingTitle = true;
	}

	function finishTitleEdit() {
		draft.title = draft.title.trim() || $messages.definitions.untitledDefinition;
		editingTitle = false;
	}

	function openDefinitionDetailsModal() {
		definitionDescriptionDraft = draft.description ?? '';
		definitionIdDraft = draft.id;
		showDefinitionAdvancedFields = false;
		showDefinitionDetailsModal = true;
	}

	function closeDefinitionDetailsModal() {
		showDefinitionDetailsModal = false;
		showDefinitionAdvancedFields = false;
		definitionDescriptionDraft = '';
		definitionIdDraft = '';
	}

	function saveDefinitionDetailsModal() {
		draft.description = definitionDescriptionDraft;
		if (showDefinitionAdvancedFields) {
			draft.id = definitionIdDraft;
		}
		closeDefinitionDetailsModal();
	}

	function openRoundModal(roundIndex: number) {
		const round = draft.rounds[roundIndex];
		if (!round) {
			return;
		}
		editingRoundIndex = roundIndex;
		roundModalTitle = round.title ?? '';
		roundModalId = round.id;
		showRoundAdvancedFields = false;
	}

	function closeRoundModal() {
		editingRoundIndex = null;
		roundModalTitle = '';
		roundModalId = '';
		showRoundAdvancedFields = false;
	}

	function saveRoundModal() {
		if (editingRoundIndex === null) {
			return;
		}
		const round = draft.rounds[editingRoundIndex];
		if (!round) {
			closeRoundModal();
			return;
		}
		round.title = roundModalTitle;
		if (showRoundAdvancedFields) {
			round.id = roundModalId;
		}
		draft.rounds = [...draft.rounds];
		closeRoundModal();
	}

	function addRound() {
		draft.rounds = [...draft.rounds, createEmptyRound(draft.rounds.length + 1)];
		openRoundModal(draft.rounds.length - 1);
	}

	function moveRound(roundIndex: number, direction: -1 | 1) {
		const targetIndex = roundIndex + direction;
		if (
			roundIndex < 0 ||
			targetIndex < 0 ||
			roundIndex >= draft.rounds.length ||
			targetIndex >= draft.rounds.length
		) {
			return;
		}
		const nextRounds = [...draft.rounds];
		[nextRounds[roundIndex], nextRounds[targetIndex]] = [
			nextRounds[targetIndex],
			nextRounds[roundIndex]
		];
		draft.rounds = nextRounds;
	}

	function requestRemoveRound(roundIndex: number) {
		const round = draft.rounds[roundIndex];
		if (!round) {
			return;
		}
		const roundLabel = round.title || `${$messages.editor.roundName} ${roundIndex + 1}`;
		pendingDelete = {
			type: 'round',
			roundIndex,
			title: $messages.editor.deleteRoundTitle(roundLabel),
			message: $messages.editor.deleteRoundMessage,
			confirmLabel: $messages.editor.deleteRoundConfirm
		};
	}

	function removeRound(roundIndex: number) {
		if (draft.rounds.length === 1) {
			draft.rounds = [createEmptyRound(1, true)];
			selectedStepKey = buildFlatSteps(draft, getStepKey)[0]?.stepKey ?? null;
			return;
		}
		const removed = draft.rounds[roundIndex];
		draft.rounds = draft.rounds.filter((_, index) => index !== roundIndex);
		if (removed.steps.some((step) => getStepKey(step) === selectedStepKey)) {
			selectedStepKey = buildFlatSteps(draft, getStepKey)[0]?.stepKey ?? null;
		}
	}

	function requestRemoveSelectedStep() {
		if (!selectedFlatStep || !selectedStep) {
			return;
		}
		const stepLabel =
			selectedStep.title?.trim() || `${$messages.editor.slide} ${selectedFlatStep.globalIndex + 1}`;
		pendingDelete = {
			type: 'step',
			title: $messages.editor.deleteStepTitle(stepLabel),
			message: $messages.editor.deleteStepMessage,
			confirmLabel: $messages.editor.deleteStepConfirm
		};
	}

	function closeDeleteModal() {
		pendingDelete = null;
	}

	function confirmDelete() {
		if (!pendingDelete) {
			return;
		}
		if (pendingDelete.type === 'round') {
			removeRound(pendingDelete.roundIndex);
		} else {
			removeSelectedStep();
		}
		closeDeleteModal();
	}

	function addStepToRound(
		roundIndex: number,
		templateId: Parameters<typeof createStepFromTemplate>[2],
		insertAt?: number
	) {
		const round = draft.rounds[roundIndex];
		if (!round) {
			return;
		}
		const stepIndex = insertAt ?? round.steps.length;
		const newStep = createStepFromTemplate(roundIndex + 1, stepIndex + 1, templateId);
		round.steps.splice(stepIndex, 0, newStep);
		draft.rounds = [...draft.rounds];
		selectedStepKey = getStepKey(newStep);
	}

	function openStepTemplatePicker() {
		if (selectedFlatStep) {
			pendingStepInsert = {
				roundIndex: selectedFlatStep.roundIndex,
				stepIndex: selectedFlatStep.stepIndex + 1
			};
		} else {
			if (draft.rounds.length === 0) {
				draft.rounds = [createEmptyRound(1)];
			}
			pendingStepInsert = {
				roundIndex: selectedRoundIndex >= 0 ? selectedRoundIndex : 0,
				stepIndex:
					selectedRoundIndex >= 0 && draft.rounds[selectedRoundIndex]
						? draft.rounds[selectedRoundIndex].steps.length
						: 0
			};
		}
		showStepTemplateModal = true;
	}

	function closeStepTemplateModal() {
		showStepTemplateModal = false;
		pendingStepInsert = null;
	}

	function addStepAfterSelected(
		templateId: Parameters<typeof createStepFromTemplate>[2] = 'blank'
	) {
		if (!pendingStepInsert) {
			if (selectedFlatStep) {
				addStepToRound(selectedFlatStep.roundIndex, templateId, selectedFlatStep.stepIndex + 1);
				return;
			}
			if (draft.rounds.length === 0) {
				draft.rounds = [createEmptyRound(1)];
			}
			addStepToRound(selectedRoundIndex >= 0 ? selectedRoundIndex : 0, templateId);
			return;
		}
		addStepToRound(pendingStepInsert.roundIndex, templateId, pendingStepInsert.stepIndex);
		closeStepTemplateModal();
	}

	function removeSelectedStep() {
		if (!selectedFlatStep) {
			return;
		}
		const { roundIndex, stepIndex, globalIndex } = selectedFlatStep;
		draft.rounds[roundIndex].steps.splice(stepIndex, 1);
		draft.rounds = [...draft.rounds];
		const nextFlatSteps = buildFlatSteps(draft, getStepKey);
		selectedStepKey =
			nextFlatSteps[Math.min(globalIndex, Math.max(0, nextFlatSteps.length - 1))]?.stepKey ?? null;
	}

	function syncCheckboxWeightedAnswer(step: StepDefinition) {
		const fallbackAnswer = buildCheckboxWeightedAnswer(step.player_input.options);
		const currentEntries = isCheckboxWeightedAnswer(step.evaluation.answer)
			? step.evaluation.answer.option_scores
			: fallbackAnswer.option_scores;
		const pointsByOption = new Map(currentEntries.map((entry) => [entry.option, entry.points]));
		step.evaluation.answer = {
			option_scores: step.player_input.options.map((option) => ({
				option,
				points: pointsByOption.get(option) ?? 0
			}))
		};
	}

	function applyEvaluationDefaults(step: StepDefinition) {
		const allowedEvaluations = INPUT_KIND_EVALUATIONS[step.player_input.kind];
		if (!allowedEvaluations.includes(step.evaluation.type_)) {
			setEvaluationType(step, DEFAULT_EVALUATION_BY_INPUT_KIND[step.player_input.kind]);
			return;
		}

		if (step.evaluation.type_ === 'ordering_match') {
			step.evaluation.answer = [...step.player_input.options];
			return;
		}
		if (step.evaluation.type_ === 'multi_select_weighted') {
			syncCheckboxWeightedAnswer(step);
			return;
		}
		if (step.evaluation.type_ === 'exact_text' && step.player_input.kind === 'radio') {
			const currentAnswer = String(step.evaluation.answer ?? '');
			step.evaluation.answer =
				step.player_input.options.find((option) => option === currentAnswer) ??
				step.player_input.options[0] ??
				'';
			return;
		}
		if (step.evaluation.type_ === 'exact_number' || step.evaluation.type_ === 'closest_number') {
			step.evaluation.answer = Number(step.evaluation.answer ?? 0);
			return;
		}
		if (Array.isArray(step.evaluation.answer) || isCheckboxWeightedAnswer(step.evaluation.answer)) {
			step.evaluation.answer = '';
		}
	}

	function setPlayerInputKind(step: StepDefinition, kind: PlayerInputKind) {
		step.player_input.kind = kind;
		if (kind === 'ordering' || kind === 'radio' || kind === 'checkbox') {
			if (step.player_input.options.length < 2) {
				step.player_input.options = [
					$messages.editor.templateMeta.trivia.options?.[0] ?? 'Option 1',
					$messages.editor.templateMeta.trivia.options?.[1] ?? 'Option 2'
				];
			}
		} else {
			step.player_input.options = [];
		}
		if (kind !== 'number') {
			step.player_input.min_value = undefined;
			step.player_input.max_value = undefined;
			step.player_input.step = undefined;
		}
		applyEvaluationDefaults(step);
	}

	function setEvaluationType(step: StepDefinition, evaluationType: EvaluationType) {
		step.evaluation.type_ = evaluationType;
		if (evaluationType === 'ordering_match') {
			step.evaluation.answer = [...step.player_input.options];
			return;
		}
		if (evaluationType === 'exact_number' || evaluationType === 'closest_number') {
			step.evaluation.answer = Number(step.evaluation.answer ?? 0);
			return;
		}
		if (evaluationType === 'multi_select_weighted') {
			syncCheckboxWeightedAnswer(step);
			return;
		}
		if (evaluationType === 'exact_text' && step.player_input.kind === 'radio') {
			const currentAnswer = String(step.evaluation.answer ?? '');
			step.evaluation.answer =
				step.player_input.options.find((option) => option === currentAnswer) ??
				step.player_input.options[0] ??
				'';
			return;
		}
		if (evaluationType === 'none') {
			step.evaluation.answer = null;
			return;
		}
		if (Array.isArray(step.evaluation.answer) || isCheckboxWeightedAnswer(step.evaluation.answer)) {
			step.evaluation.answer = '';
		}
	}

	function addInputOption(step: StepDefinition) {
		step.player_input.options.push(
			`${$messages.common.add} ${step.player_input.options.length + 1}`
		);
		if (step.evaluation.type_ === 'ordering_match') {
			step.evaluation.answer = [...step.player_input.options];
			return;
		}
		if (step.evaluation.type_ === 'multi_select_weighted') {
			syncCheckboxWeightedAnswer(step);
			return;
		}
		if (step.evaluation.type_ === 'exact_text' && step.player_input.kind === 'radio') {
			step.evaluation.answer = step.player_input.options[0] ?? '';
		}
	}

	function removeInputOption(step: StepDefinition, optionIndex: number) {
		const removedOption = step.player_input.options[optionIndex];
		step.player_input.options.splice(optionIndex, 1);
		if (step.evaluation.type_ === 'ordering_match') {
			step.evaluation.answer = [...step.player_input.options];
			return;
		}
		if (step.evaluation.type_ === 'multi_select_weighted') {
			syncCheckboxWeightedAnswer(step);
			return;
		}
		if (step.evaluation.type_ === 'exact_text' && step.player_input.kind === 'radio') {
			if (step.evaluation.answer === removedOption) {
				step.evaluation.answer = step.player_input.options[0] ?? '';
			}
		}
	}

	function setOrderingAnswer(step: StepDefinition, optionIndex: number, value: string) {
		const answer = Array.isArray(step.evaluation.answer)
			? step.evaluation.answer.map((item) => String(item))
			: [...step.player_input.options];
		answer[optionIndex] = value;
		step.evaluation.answer = answer;
	}

	function setInputOptionValue(step: StepDefinition, optionIndex: number, value: string) {
		const previousValue = step.player_input.options[optionIndex] ?? '';
		const previousCheckboxScores = getCheckboxOptionScores(step);
		step.player_input.options[optionIndex] = value;
		if (step.evaluation.type_ === 'ordering_match') {
			step.evaluation.answer = [...step.player_input.options];
			return;
		}
		if (step.evaluation.type_ === 'multi_select_weighted') {
			const currentScores = step.player_input.options.map((option, index) =>
				index === optionIndex
					? { option: value, points: previousCheckboxScores[index]?.points ?? 0 }
					: { option, points: previousCheckboxScores[index]?.points ?? 0 }
			);
			step.evaluation.answer = { option_scores: currentScores };
			return;
		}
		if (step.evaluation.type_ === 'exact_text' && step.player_input.kind === 'radio') {
			if (step.evaluation.answer === previousValue) {
				step.evaluation.answer = value;
			}
		}
	}

	function setRadioCorrectOption(step: StepDefinition, option: string) {
		step.evaluation.answer = option;
	}

	function setCheckboxOptionPoints(step: StepDefinition, optionIndex: number, points: number) {
		const nextScores = getCheckboxOptionScores(step).map((entry, index) =>
			index === optionIndex ? { ...entry, points } : entry
		);
		step.evaluation.answer = { option_scores: nextScores };
	}

	function addMedia(step: StepDefinition) {
		step.media = {
			type_: 'image',
			src: '',
			reveal: 'none',
			loop: false
		};
	}

	function removeMedia(step: StepDefinition) {
		step.media = undefined;
	}

	function updateMediaType(step: StepDefinition, mediaType: (typeof MEDIA_TYPES)[number]) {
		if (!step.media) {
			addMedia(step);
		}
		if (!step.media) {
			return;
		}
		step.media.type_ = mediaType;
		if (mediaType !== 'image') {
			step.media.reveal = 'none';
		}
	}

	function buildPayload(): GameDefinition {
		return {
			id: draft.id.trim(),
			title: draft.title.trim(),
			description: draft.description?.trim() || undefined,
			rounds: draft.rounds.map((round) => ({
				id: round.id.trim(),
				title: round.title?.trim() || undefined,
				steps: round.steps.map((step) => ({
					id: step.id.trim(),
					title: step.title.trim(),
					body: step.body?.trim() || undefined,
					timer: {
						seconds: step.timer.seconds ?? undefined,
						enforced: step.timer.enforced
					},
					player_input: {
						kind: step.player_input.kind,
						prompt: step.player_input.prompt?.trim() || undefined,
						placeholder: step.player_input.placeholder?.trim() || undefined,
						options: step.player_input.options.map((option) => option.trim()).filter(Boolean),
						min_value: step.player_input.min_value ?? undefined,
						max_value: step.player_input.max_value ?? undefined,
						step: step.player_input.step ?? undefined
					},
					evaluation: {
						type_: step.evaluation.type_,
						points: step.evaluation.points,
						answer: normalizeAnswer(step)
					},
					host_behavior: {
						reveal_answers: step.host_behavior.reveal_answers,
						show_submissions: step.host_behavior.show_submissions,
						allow_custom_points: step.host_behavior.allow_custom_points
					},
					media:
						step.media && step.media.src.trim()
							? {
									type_: step.media.type_,
									src: step.media.src.trim(),
									reveal: step.media.reveal,
									loop: step.media.loop
								}
							: undefined
				}))
			}))
		};
	}

	function getStepKeyByIdentity(
		definition: GameDefinition,
		target: {
			stepId?: string;
			roundIndex: number;
			stepIndex: number;
		}
	): string | null {
		const steps = buildFlatSteps(definition, getStepKey);
		if (target.stepId) {
			const matchingStep = steps.find((item) => item.step.id === target.stepId);
			if (matchingStep) {
				return matchingStep.stepKey;
			}
		}
		const fallbackStep = definition.rounds[target.roundIndex]?.steps[target.stepIndex];
		return fallbackStep ? getStepKey(fallbackStep) : (steps[0]?.stepKey ?? null);
	}

	async function saveDefinition() {
		finishTitleEdit();
		saving = true;
		errorMessage = '';
		statusMessage = '';
		const selectionBeforeSave = selectedFlatStep
			? {
					stepId: selectedFlatStep.step.id,
					roundIndex: selectedFlatStep.roundIndex,
					stepIndex: selectedFlatStep.stepIndex
				}
			: null;
		const payload = buildPayload();
		const endpoint = isNewDefinition
			? '/api/v1/definitions'
			: `/api/v1/definitions/${persistedDefinitionId}`;
		const response = await fetch(endpoint, {
			method: isNewDefinition ? 'POST' : 'PUT',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(payload)
		});
		saving = false;
		if (!response.ok) {
			const detail = await readErrorDetail(response);
			errorMessage = detail || $messages.definitions.couldNotSaveDefinition;
			return;
		}
		const wasNewDefinition = isNewDefinition;
		draft = structuredClone(await response.json());
		persistedDefinitionId = draft.id;
		isNewDefinition = false;
		selectedStepKey = selectionBeforeSave
			? getStepKeyByIdentity(draft, selectionBeforeSave)
			: (buildFlatSteps(draft, getStepKey)[0]?.stepKey ?? null);
		statusMessage = $messages.definitions.definitionSaved;
		if (wasNewDefinition) {
			goto(`/definitions/${draft.id}`, { replaceState: true });
		}
	}

	async function uploadMedia(event: Event, step: StepDefinition, stepId: string) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) {
			return;
		}
		if (!step.media) {
			addMedia(step);
		}
		if (!step.media) {
			return;
		}
		uploadKey = stepId;
		uploadError = '';
		const response = await fetch(
			`/api/v1/media?kind=${step.media.type_}&filename=${encodeURIComponent(file.name)}`,
			{
				method: 'POST',
				headers: {
					'Content-Type': file.type || 'application/octet-stream'
				},
				body: file
			}
		);
		uploadKey = null;
		if (!response.ok) {
			uploadError = (await readErrorDetail(response)) || 'Could not upload media.';
			input.value = '';
			return;
		}
		const asset: MediaAsset = await response.json();
		step.media.src = asset.public_url;
		input.value = '';
	}

	async function readErrorDetail(response: Response): Promise<string> {
		try {
			const payload = await response.json();
			if (typeof payload?.detail === 'string') {
				return payload.detail;
			}
		} catch {
			return '';
		}
		return '';
	}

	function onStepDragStart(event: PointerEvent, stepKey: string) {
		const card = event.currentTarget as HTMLElement | null;
		const rect = card?.getBoundingClientRect();
		pendingDragKey = stepKey;
		dragStartPointer = { x: event.clientX, y: event.clientY };
		dragPointer = { x: event.clientX, y: event.clientY };
		if (rect) {
			dragPointerOffset = {
				x: event.clientX - rect.left,
				y: event.clientY - rect.top
			};
			dragCardWidth = rect.width;
		}
	}

	function onStepDragMove(event: PointerEvent) {
		if (!pendingDragKey && !draggedStepKey) {
			return;
		}
		dragPointer = {
			x: event.clientX,
			y: event.clientY
		};
		if (!draggedStepKey && pendingDragKey) {
			const distance = Math.hypot(
				event.clientX - dragStartPointer.x,
				event.clientY - dragStartPointer.y
			);
			if (distance >= 6) {
				draggedStepKey = pendingDragKey;
				dropTargetKey = null;
				dragPreviewDefinition = null;
				selectedStepKey = pendingDragKey;
			}
		}
	}

	function onStepDragEnd() {
		pendingDragKey = null;
		draggedStepKey = null;
		dropTargetKey = null;
		dragPreviewDefinition = null;
		dragPointer = { x: 0, y: 0 };
		dragPointerOffset = { x: 0, y: 0 };
		dragStartPointer = { x: 0, y: 0 };
	}

	function buildReorderedDefinition(
		definition: GameDefinition,
		sourceStepKey: string,
		targetRoundIndex: number,
		targetStepIndex: number
	): GameDefinition | null {
		const source = buildFlatSteps(definition, getStepKey).find(
			(item) => item.stepKey === sourceStepKey
		);
		const targetRound = definition.rounds[targetRoundIndex];
		if (!source || !targetRound) {
			return null;
		}
		const nextRounds = definition.rounds.map((round) => ({
			...round,
			steps: [...round.steps]
		}));
		const [step] = nextRounds[source.roundIndex].steps.splice(source.stepIndex, 1);
		if (!step) {
			return null;
		}

		const adjustedTargetIndex =
			source.roundIndex === targetRoundIndex && source.stepIndex < targetStepIndex
				? targetStepIndex - 1
				: targetStepIndex;
		const insertIndex = Math.max(
			0,
			Math.min(adjustedTargetIndex, nextRounds[targetRoundIndex].steps.length)
		);

		const existingIndex = nextRounds[targetRoundIndex].steps.findIndex(
			(candidate) => getStepKey(candidate) === sourceStepKey
		);
		if (existingIndex === insertIndex) {
			return definition;
		}

		nextRounds[targetRoundIndex].steps.splice(insertIndex, 0, step);
		return {
			...definition,
			rounds: nextRounds
		};
	}

	function activateDropTarget(key: string, targetRoundIndex: number, targetStepIndex: number) {
		if (!draggedStepKey) {
			return;
		}
		dropTargetKey = key;
		const nextPreview = buildReorderedDefinition(
			draft,
			draggedStepKey,
			targetRoundIndex,
			targetStepIndex
		);
		if (!nextPreview) {
			return;
		}
		dragPreviewDefinition = nextPreview === draft ? null : nextPreview;
	}

	function onDropStep(targetRoundIndex: number, targetStepIndex: number, key: string) {
		const sourceStepKey = draggedStepKey;
		if (!sourceStepKey) {
			return;
		}
		const nextPreview = buildReorderedDefinition(
			draft,
			sourceStepKey,
			targetRoundIndex,
			targetStepIndex
		);
		if (nextPreview && nextPreview !== draft) {
			draft = nextPreview;
			dragPreviewDefinition = null;
			selectedStepKey = sourceStepKey;
		} else {
			dragPreviewDefinition = null;
		}
		dropTargetKey = key;
	}

	function isTextEditingTarget(target: EventTarget | null) {
		const element = target instanceof HTMLElement ? target : null;
		if (!element) {
			return false;
		}
		const tagName = element.tagName.toLowerCase();
		return (
			tagName === 'input' ||
			tagName === 'textarea' ||
			tagName === 'select' ||
			element.isContentEditable
		);
	}

	function selectRelativeStep(offset: -1 | 1) {
		if (selectedStepPosition < 0) {
			return;
		}
		selectStep(flatSteps[selectedStepPosition + offset]?.stepKey);
	}

	function handleEditorShortcuts(event: KeyboardEvent) {
		const isMac = navigator.platform.toLowerCase().includes('mac');
		const modifierPressed = isMac ? event.metaKey : event.ctrlKey;
		const isTypingTarget = isTextEditingTarget(event.target);

		if (modifierPressed && event.key.toLowerCase() === 's') {
			event.preventDefault();
			saveDefinition();
			return;
		}

		if (modifierPressed && event.shiftKey && event.key.toLowerCase() === 'p') {
			event.preventDefault();
			openPreview();
			return;
		}

		if (isTypingTarget) {
			return;
		}

		if (modifierPressed && event.shiftKey && event.key.toLowerCase() === 'a') {
			event.preventDefault();
			openStepTemplatePicker();
			return;
		}

		if (modifierPressed && event.key === ',') {
			event.preventDefault();
			showAdvancedFields = !showAdvancedFields;
			return;
		}

		if (modifierPressed && (event.key === 'Backspace' || event.key === 'Delete')) {
			event.preventDefault();
			requestRemoveSelectedStep();
			return;
		}

		if (event.altKey && event.key === 'ArrowUp') {
			event.preventDefault();
			selectRelativeStep(-1);
			return;
		}

		if (event.altKey && event.key === 'ArrowDown') {
			event.preventDefault();
			selectRelativeStep(1);
			return;
		}

		if (!event.metaKey && !event.ctrlKey && !event.altKey && event.key === '?') {
			event.preventDefault();
			openShortcutHelp();
		}
	}
</script>

<svelte:window onkeydown={handleEditorShortcuts} />

<div class="flex h-full min-h-0 flex-col">
	<section class="card flex min-h-0 flex-1 flex-col overflow-hidden p-0">
		<DefinitionEditorToolbar
			title={displayDefinition.title}
			{breadcrumbCurrentLabel}
			{editingTitle}
			{saving}
			{loadingEditor}
			onGoHome={() => goto('/')}
			onManageDefinitions={() => goto('/definitions')}
			onSave={saveDefinition}
			onAddStep={openStepTemplatePicker}
			onAddRound={addRound}
			onOpenDetails={openDefinitionDetailsModal}
			onStartTitleEdit={beginTitleEdit}
			onFinishTitleEdit={finishTitleEdit}
			onTitleChange={(value) => (draft.title = value)}
		/>

		<div class="grid min-h-0 flex-1 gap-0 xl:grid-cols-[22rem_minmax(0,1fr)]">
			<div
				class="min-h-0 overflow-hidden border-b border-slate-200 bg-white/55 pl-3 pt-2 xl:border-b-0 xl:border-r"
			>
				<DefinitionStepSorter
					rounds={displayDefinition.rounds}
					{flatSteps}
					{selectedStepKey}
					{draggedStepKey}
					{dropTargetKey}
					onSelectStep={selectStep}
					onOpenRoundModal={openRoundModal}
					{moveRound}
					onRemoveRound={requestRemoveRound}
					{onStepDragStart}
					{onStepDragMove}
					{onStepDragEnd}
					onActivateDropTarget={activateDropTarget}
					{onDropStep}
					draggedItem={draggedFlatStep}
					dragPointerX={dragPointer.x}
					dragPointerY={dragPointer.y}
					dragOffsetX={dragPointerOffset.x}
					dragOffsetY={dragPointerOffset.y}
					{dragCardWidth}
				/>
			</div>

			<div class="min-h-0 overflow-hidden bg-white/40 pt-2">
				{#if errorMessage}
					<div class="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-red-700">
						{errorMessage}
					</div>
				{/if}
				{#if statusMessage}
					<div
						class="mb-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-700"
					>
						{statusMessage}
					</div>
				{/if}
				{#if uploadError}
					<div
						class="mb-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-700"
					>
						{uploadError}
					</div>
				{/if}

				{#if loadingEditor}
					<p class="text-slate-500">Loading definition...</p>
				{:else if selectedStep && selectedFlatStep}
					<DefinitionStepEditor
						{selectedStep}
						{selectedFlatStep}
						{selectedStepPosition}
						totalSteps={flatSteps.length}
						{showAdvancedFields}
						{uploadKey}
						onToggleAdvancedFields={() => (showAdvancedFields = !showAdvancedFields)}
						onSelectStep={selectStep}
						onAddStepAfter={openStepTemplatePicker}
						onRemoveSelectedStep={requestRemoveSelectedStep}
						onPreview={openPreview}
						onOpenShortcutHelp={openShortcutHelp}
						onSetPlayerInputKind={setPlayerInputKind}
						onSetEvaluationType={setEvaluationType}
						onAddInputOption={addInputOption}
						onRemoveInputOption={removeInputOption}
						onSetInputOptionValue={setInputOptionValue}
						onSetOrderingAnswer={setOrderingAnswer}
						onSetRadioCorrectOption={setRadioCorrectOption}
						onSetCheckboxOptionPoints={setCheckboxOptionPoints}
						onAddMedia={addMedia}
						onRemoveMedia={removeMedia}
						onUpdateMediaType={updateMediaType}
						onUploadMedia={uploadMedia}
						{flatSteps}
					/>
				{:else}
					<div
						class="flex min-h-[28rem] flex-col items-center justify-center rounded-3xl border border-dashed border-slate-300 bg-slate-50/70 p-8 text-center"
					>
						<h3 class="label-title text-2xl">No Step Selected</h3>
						<p class="mt-2 max-w-lg text-slate-600">
							Create a new step from the sorter or add one to a round to start authoring slides.
						</p>
						<button class="btn btn-primary mt-4" type="button" onclick={openStepTemplatePicker}>
							Create First Step
						</button>
					</div>
				{/if}
			</div>
		</div>
	</section>
</div>

{#if editingRoundIndex !== null}
	<DefinitionRoundModal
		{roundModalTitle}
		{roundModalId}
		{showRoundAdvancedFields}
		onRoundModalTitleChange={(value) => (roundModalTitle = value)}
		onRoundModalIdChange={(value) => (roundModalId = value)}
		onToggleAdvancedFields={() => (showRoundAdvancedFields = !showRoundAdvancedFields)}
		onClose={closeRoundModal}
		onSave={saveRoundModal}
	/>
{/if}

{#if showDefinitionDetailsModal}
	<DefinitionDetailsModal
		description={definitionDescriptionDraft}
		definitionId={definitionIdDraft}
		showAdvancedFields={showDefinitionAdvancedFields}
		{isNewDefinition}
		currentDefinitionId={draft.id}
		onDescriptionChange={(value) => (definitionDescriptionDraft = value)}
		onDefinitionIdChange={(value) => (definitionIdDraft = value)}
		onToggleAdvancedFields={() => (showDefinitionAdvancedFields = !showDefinitionAdvancedFields)}
		onClose={closeDefinitionDetailsModal}
		onSave={saveDefinitionDetailsModal}
	/>
{/if}

{#if showPreviewModal}
	<DefinitionPreviewModal step={previewStep} countdown={previewCountdown} onClose={closePreview} />
{/if}

{#if showShortcutHelpModal}
	<DefinitionShortcutHelpModal groups={shortcutGroups} onClose={closeShortcutHelp} />
{/if}

{#if showStepTemplateModal}
	<DefinitionStepTemplateModal
		templates={getStepTemplates()}
		onClose={closeStepTemplateModal}
		onSelectTemplate={addStepAfterSelected}
	/>
{/if}

{#if pendingDelete}
	<DefinitionConfirmModal
		title={pendingDelete.title}
		message={pendingDelete.message}
		confirmLabel={pendingDelete.confirmLabel}
		onClose={closeDeleteModal}
		onConfirm={confirmDelete}
	/>
{/if}
