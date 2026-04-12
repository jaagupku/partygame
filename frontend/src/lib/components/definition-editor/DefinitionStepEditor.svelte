<script lang="ts">
	import 'iconify-icon';
	import {
		IMAGE_REVEALS,
		INPUT_KIND_EVALUATIONS,
		INPUT_KINDS,
		MEDIA_TYPES,
		getCheckboxOptionScores,
		getNumberAnswer,
		getOrderingAnswer,
		getTextAnswer
	} from './helpers';
	import type { FlatStepItem } from './types';

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
		onSetOrderingAnswer: (step: StepDefinition, optionIndex: number, value: string) => void;
		onSetRadioCorrectOption: (step: StepDefinition, option: string) => void;
		onSetCheckboxOptionPoints: (step: StepDefinition, optionIndex: number, points: number) => void;
		onAddMedia: (step: StepDefinition) => void;
		onRemoveMedia: (step: StepDefinition) => void;
		onUpdateMediaType: (step: StepDefinition, mediaType: (typeof MEDIA_TYPES)[number]) => void;
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
		onSetOrderingAnswer,
		onSetRadioCorrectOption,
		onSetCheckboxOptionPoints,
		onAddMedia,
		onRemoveMedia,
		onUpdateMediaType,
		onUploadMedia,
		flatSteps
	}: Props = $props();

	const availableEvaluationTypes = $derived(INPUT_KIND_EVALUATIONS[selectedStep.player_input.kind]);
	const checkboxOptionScores = $derived(getCheckboxOptionScores(selectedStep));

	type HeaderAction = {
		label: string;
		shortcut?: string;
		icon: string;
		onClick: () => void;
		disabled?: boolean;
		variant?: 'default' | 'danger';
	};

	function getTooltipText(action: HeaderAction) {
		return action.shortcut ? `${action.label} — ${action.shortcut}` : action.label;
	}

	const headerActions = $derived<HeaderAction[]>([
		{
			label: showAdvancedFields ? 'Hide Advanced' : 'Show Advanced',
			shortcut: 'Cmd/Ctrl + ,',
			icon: 'fluent:settings-16-filled',
			onClick: onToggleAdvancedFields
		},
		{
			label: 'Previous Step',
			shortcut: 'Alt + ArrowUp',
			icon: 'fluent:chevron-left-16-filled',
			onClick: () => onSelectStep(flatSteps[selectedStepPosition - 1]?.stepKey),
			disabled: selectedStepPosition <= 0
		},
		{
			label: 'Next Step',
			shortcut: 'Alt + ArrowDown',
			icon: 'fluent:chevron-right-16-filled',
			onClick: () => onSelectStep(flatSteps[selectedStepPosition + 1]?.stepKey),
			disabled: selectedStepPosition < 0 || selectedStepPosition >= totalSteps - 1
		},
		{
			label: 'Preview',
			shortcut: 'Cmd/Ctrl + Shift + P',
			icon: 'fluent:desktop-16-filled',
			onClick: onPreview
		},
		{
			label: 'Delete Step',
			shortcut: 'Cmd/Ctrl + Backspace/Delete',
			icon: 'fluent:delete-16-filled',
			onClick: onRemoveSelectedStep,
			variant: 'danger'
		},
		{
			label: 'Shortcuts',
			shortcut: '?',
			icon: 'fluent:question-circle-16-filled',
			onClick: onOpenShortcutHelp
		}
	]);
</script>

<section class="flex h-full min-h-0 flex-col rounded-3xl border border-slate-200 bg-white/70 p-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div>
			<p class="text-sm font-bold uppercase tracking-wide text-slate-500">
				{selectedFlatStep.roundTitle} · Slide {selectedFlatStep.globalIndex + 1}
			</p>
			<h2 class="label-title text-2xl">{selectedStep.title || 'Selected Step'}</h2>
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
				title="Add Step After — Cmd/Ctrl + Shift + A"
			>
				<iconify-icon icon="fluent:add-16-filled"></iconify-icon>
				Add Step After
			</button>
		</div>
	</div>

	<div class="mt-4 min-h-0 flex-1 overflow-y-auto pr-2">
		<div class="grid gap-3">
			<label class="input-wrap">
				<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Title</span>
				<input bind:value={selectedStep.title} class="input text-lg" />
			</label>
			<label class="input-wrap">
				<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Body</span>
				<textarea bind:value={selectedStep.body} class="input min-h-24 text-lg"></textarea>
			</label>
			{#if showAdvancedFields}
				<label class="input-wrap">
					<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Step id</span>
					<input bind:value={selectedStep.id} class="input text-lg" />
				</label>
			{/if}
		</div>

		<div class="mt-4 grid gap-3 md:grid-cols-2">
			<label class="input-wrap">
				<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Input kind</span>
				<div class="select-shell">
					<select
						class="input select-input text-lg"
						value={selectedStep.player_input.kind}
						onchange={(event) =>
							onSetPlayerInputKind(
								selectedStep,
								(event.currentTarget as HTMLSelectElement).value as PlayerInputKind
							)}
					>
						{#each INPUT_KINDS as kind}
							<option value={kind}>{kind}</option>
						{/each}
					</select>
					<span class="select-chevron" aria-hidden="true">▾</span>
				</div>
			</label>
			<label class="input-wrap">
				<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Evaluation</span>
				<div class="select-shell">
					<select
						class="input select-input text-lg"
						value={selectedStep.evaluation.type_}
						onchange={(event) =>
							onSetEvaluationType(
								selectedStep,
								(event.currentTarget as HTMLSelectElement).value as EvaluationType
							)}
					>
						{#each availableEvaluationTypes as evaluationType}
							<option value={evaluationType}>{evaluationType}</option>
						{/each}
					</select>
					<span class="select-chevron" aria-hidden="true">▾</span>
				</div>
			</label>
			<label class="input-wrap">
				<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Timer seconds</span>
				<input
					bind:value={selectedStep.timer.seconds}
					type="number"
					min="0"
					class="input text-lg"
				/>
			</label>
			<label class="flex items-center justify-between gap-4 rounded-2xl bg-white/80 px-4 py-3">
				<div>
					<p class="text-lg font-bold">Enforced timer</p>
					<p class="text-sm text-slate-600">Automatically close the step at zero.</p>
				</div>
				<input bind:checked={selectedStep.timer.enforced} type="checkbox" class="h-5 w-5" />
			</label>
		</div>

		<div class="mt-4 grid gap-3 md:grid-cols-2">
			<label class="input-wrap">
				<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Input prompt</span>
				<input bind:value={selectedStep.player_input.prompt} class="input text-lg" />
			</label>
			<label class="input-wrap">
				<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Placeholder</span>
				<input bind:value={selectedStep.player_input.placeholder} class="input text-lg" />
			</label>
			{#if selectedStep.evaluation.type_ !== 'multi_select_weighted'}
				<label class="input-wrap">
					<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Points</span>
					<input bind:value={selectedStep.evaluation.points} type="number" class="input text-lg" />
				</label>
			{/if}
		</div>

		{#if selectedStep.player_input.kind === 'number'}
			<div class="mt-4 grid gap-3 md:grid-cols-3">
				<label class="input-wrap">
					<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Min value</span>
					<input
						bind:value={selectedStep.player_input.min_value}
						type="number"
						class="input text-lg"
					/>
				</label>
				<label class="input-wrap">
					<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Max value</span>
					<input
						bind:value={selectedStep.player_input.max_value}
						type="number"
						class="input text-lg"
					/>
				</label>
				<label class="input-wrap">
					<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Slider step</span>
					<input
						bind:value={selectedStep.player_input.step}
						type="number"
						min="0"
						class="input text-lg"
					/>
				</label>
			</div>
		{/if}

		{#if ['ordering', 'radio', 'checkbox'].includes(selectedStep.player_input.kind)}
			<div class="mt-4 rounded-2xl bg-white/80 p-4">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<p class="text-lg font-bold">
						{selectedStep.player_input.kind === 'ordering'
							? 'Ordering options'
							: selectedStep.player_input.kind === 'radio'
								? 'Radio button options'
								: 'Checkbox options'}
					</p>
					<button
						class="btn btn-ghost text-sm"
						type="button"
						onclick={() => onAddInputOption(selectedStep)}
					>
						Add Option
					</button>
				</div>
				<div class="mt-3 grid gap-3">
					{#each selectedStep.player_input.options as _, optionIndex}
						<div
							class={`grid gap-3 ${
								selectedStep.player_input.kind === 'checkbox' &&
								selectedStep.evaluation.type_ === 'multi_select_weighted'
									? 'md:grid-cols-[1fr_8rem_auto]'
									: selectedStep.player_input.kind === 'radio' &&
										  selectedStep.evaluation.type_ === 'exact_text'
										? 'md:grid-cols-[1fr_auto_auto]'
										: 'md:grid-cols-[1fr_auto]'
							}`}
						>
							<input
								value={selectedStep.player_input.options[optionIndex]}
								class="input text-lg"
								oninput={(event) =>
									onSetInputOptionValue(
										selectedStep,
										optionIndex,
										(event.currentTarget as HTMLInputElement).value
									)}
							/>
							{#if selectedStep.player_input.kind === 'radio' && selectedStep.evaluation.type_ === 'exact_text'}
								<label
									class="flex items-center gap-2 rounded-2xl bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700"
								>
									<input
										type="radio"
										name={`radio-correct-${selectedStep.id}`}
										checked={selectedStep.evaluation.answer ===
											selectedStep.player_input.options[optionIndex]}
										onchange={() =>
											onSetRadioCorrectOption(
												selectedStep,
												selectedStep.player_input.options[optionIndex] ?? ''
											)}
									/>
									Correct
								</label>
							{:else if selectedStep.player_input.kind === 'checkbox' && selectedStep.evaluation.type_ === 'multi_select_weighted'}
								<label class="input-wrap">
									<span class="text-xs font-bold uppercase tracking-wide text-slate-500">
										Points
									</span>
									<input
										class="input text-lg"
										type="number"
										value={checkboxOptionScores[optionIndex]?.points ?? 0}
										oninput={(event) =>
											onSetCheckboxOptionPoints(
												selectedStep,
												optionIndex,
												Number((event.currentTarget as HTMLInputElement).value || 0)
											)}
									/>
								</label>
							{/if}
							<button
								class="btn btn-danger text-sm"
								type="button"
								onclick={() => onRemoveInputOption(selectedStep, optionIndex)}
							>
								Remove
							</button>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		{#if selectedStep.evaluation.type_ === 'ordering_match'}
			<div class="mt-4 rounded-2xl bg-white/80 p-4">
				<p class="text-lg font-bold">Correct order</p>
				<div class="mt-3 grid gap-3">
					{#each getOrderingAnswer(selectedStep) as answerValue, optionIndex}
						<input
							value={answerValue}
							class="input text-lg"
							oninput={(event) =>
								onSetOrderingAnswer(
									selectedStep,
									optionIndex,
									(event.currentTarget as HTMLInputElement).value
								)}
						/>
					{/each}
				</div>
			</div>
		{:else if selectedStep.evaluation.type_ === 'exact_number' || selectedStep.evaluation.type_ === 'closest_number'}
			<label class="input-wrap mt-4">
				<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Correct number</span>
				<input
					class="input text-lg"
					type="number"
					value={getNumberAnswer(selectedStep)}
					oninput={(event) =>
						(selectedStep.evaluation.answer = (event.currentTarget as HTMLInputElement).value)}
				/>
			</label>
		{:else if selectedStep.evaluation.type_ === 'multi_select_weighted'}
			<div class="mt-4 rounded-2xl bg-white/80 p-4">
				<p class="text-lg font-bold">Checkbox scoring</p>
				<p class="mt-2 text-sm text-slate-600">
					Each selected option awards its configured points. Negative values subtract points.
				</p>
			</div>
		{:else if selectedStep.evaluation.type_ === 'exact_text' && selectedStep.player_input.kind === 'radio'}
			<div class="mt-4 rounded-2xl bg-white/80 p-4">
				<p class="text-lg font-bold">Correct option</p>
				<p class="mt-2 text-sm text-slate-600">
					Mark the correct choice directly in the option list above.
				</p>
			</div>
		{:else if selectedStep.evaluation.type_ !== 'none'}
			<label class="input-wrap mt-4">
				<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Answer / rubric</span
				>
				<input
					class="input text-lg"
					value={getTextAnswer(selectedStep)}
					oninput={(event) =>
						(selectedStep.evaluation.answer = (event.currentTarget as HTMLInputElement).value)}
				/>
			</label>
		{/if}

		<div class="mt-4 rounded-2xl bg-white/80 p-4">
			<p class="text-lg font-bold">Host controls</p>
			<div class="mt-3 grid gap-3 md:grid-cols-3">
				<label class="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3">
					<span class="text-sm font-semibold">Reveal answers</span>
					<input
						bind:checked={selectedStep.host_behavior.reveal_answers}
						type="checkbox"
						class="h-5 w-5"
					/>
				</label>
				<label class="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3">
					<span class="text-sm font-semibold">Show submissions</span>
					<input
						bind:checked={selectedStep.host_behavior.show_submissions}
						type="checkbox"
						class="h-5 w-5"
					/>
				</label>
				<label class="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3">
					<span class="text-sm font-semibold">Custom points</span>
					<input
						bind:checked={selectedStep.host_behavior.allow_custom_points}
						type="checkbox"
						class="h-5 w-5"
					/>
				</label>
			</div>
		</div>

		<div class="mt-4 rounded-2xl bg-white/80 p-4">
			<div class="flex flex-wrap items-center justify-between gap-3">
				<p class="text-lg font-bold">Media</p>
				{#if selectedStep.media}
					<button
						class="btn btn-danger text-sm"
						type="button"
						onclick={() => onRemoveMedia(selectedStep)}
					>
						Remove Media
					</button>
				{:else}
					<button
						class="btn btn-ghost text-sm"
						type="button"
						onclick={() => onAddMedia(selectedStep)}
					>
						Add Media
					</button>
				{/if}
			</div>

			{#if selectedStep.media}
				<div class="mt-3 grid gap-3">
					<label class="input-wrap">
						<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Media type</span>
						<div class="select-shell">
							<select
								class="input select-input text-lg"
								value={selectedStep.media.type_}
								onchange={(event) =>
									onUpdateMediaType(
										selectedStep,
										(event.currentTarget as HTMLSelectElement).value as (typeof MEDIA_TYPES)[number]
									)}
							>
								{#each MEDIA_TYPES as mediaType}
									<option value={mediaType}>{mediaType}</option>
								{/each}
							</select>
							<span class="select-chevron" aria-hidden="true">▾</span>
						</div>
					</label>

					<label class="input-wrap">
						<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Source URL</span>
						<input
							bind:value={selectedStep.media.src}
							class="input text-lg"
							placeholder="/api/v1/media/..."
						/>
					</label>

					{#if selectedStep.media.type_ === 'image'}
						<label class="input-wrap">
							<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
								>Reveal mode</span
							>
							<div class="select-shell">
								<select bind:value={selectedStep.media.reveal} class="input select-input text-lg">
									{#each IMAGE_REVEALS as revealMode}
										<option value={revealMode}>{revealMode}</option>
									{/each}
								</select>
								<span class="select-chevron" aria-hidden="true">▾</span>
							</div>
						</label>
					{/if}

					<label class="flex items-center justify-between gap-4 rounded-2xl bg-slate-50 px-4 py-3">
						<div>
							<p class="text-lg font-bold">Loop media</p>
							<p class="text-sm text-slate-600">
								Useful for short ambient clips and repeatable audio.
							</p>
						</div>
						<input bind:checked={selectedStep.media.loop} type="checkbox" class="h-5 w-5" />
					</label>

					<label class="input-wrap">
						<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Upload file</span
						>
						<input
							type="file"
							class="input text-base file:mr-4 file:rounded-xl file:border-0 file:bg-sky-100 file:px-3 file:py-2 file:font-semibold file:text-sky-700"
							onchange={(event) => onUploadMedia(event, selectedStep, selectedStep.id)}
						/>
					</label>

					{#if uploadKey === selectedStep.id}
						<p class="text-sm text-sky-700">Uploading media...</p>
					{/if}

					{#if selectedStep.media.src}
						<div class="rounded-2xl bg-slate-50 p-3 text-sm text-slate-600">
							Saved media source: {selectedStep.media.src}
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
</section>
