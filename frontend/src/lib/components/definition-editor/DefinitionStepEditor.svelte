<script lang="ts">
	import {
		EVALUATION_TYPES,
		IMAGE_REVEALS,
		INPUT_KINDS,
		MEDIA_TYPES,
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
		onSetPlayerInputKind: (step: StepDefinition, kind: PlayerInputKind) => void;
		onSetEvaluationType: (step: StepDefinition, evaluationType: EvaluationType) => void;
		onAddInputOption: (step: StepDefinition) => void;
		onRemoveInputOption: (step: StepDefinition, optionIndex: number) => void;
		onSetOrderingAnswer: (step: StepDefinition, optionIndex: number, value: string) => void;
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
		onSetPlayerInputKind,
		onSetEvaluationType,
		onAddInputOption,
		onRemoveInputOption,
		onSetOrderingAnswer,
		onAddMedia,
		onRemoveMedia,
		onUpdateMediaType,
		onUploadMedia,
		flatSteps
	}: Props = $props();
</script>

<section class="flex h-full min-h-0 flex-col rounded-3xl border border-slate-200 bg-white/70 p-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div>
			<p class="text-sm font-bold uppercase tracking-wide text-slate-500">
				{selectedFlatStep.roundTitle} · Slide {selectedFlatStep.globalIndex + 1}
			</p>
			<h2 class="label-title text-2xl">{selectedStep.title || 'Selected Step'}</h2>
		</div>
		<div class="flex flex-wrap gap-2">
			<button
				class="btn btn-ghost px-4 py-2 text-sm"
				type="button"
				onclick={onToggleAdvancedFields}
			>
				{showAdvancedFields ? 'Hide Advanced' : 'Show Advanced'}
			</button>
			<button
				class="btn btn-ghost px-4 py-2 text-sm"
				type="button"
				onclick={() => onSelectStep(flatSteps[selectedStepPosition - 1]?.stepKey)}
				disabled={selectedStepPosition <= 0}
			>
				Previous
			</button>
			<button
				class="btn btn-ghost px-4 py-2 text-sm"
				type="button"
				onclick={() => onSelectStep(flatSteps[selectedStepPosition + 1]?.stepKey)}
				disabled={selectedStepPosition < 0 || selectedStepPosition >= totalSteps - 1}
			>
				Next
			</button>
			<button class="btn btn-accent px-4 py-2 text-sm" type="button" onclick={onAddStepAfter}>
				Add Step After
			</button>
			<button class="btn btn-danger px-4 py-2 text-sm" type="button" onclick={onRemoveSelectedStep}>
				Delete Step
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
						{#each EVALUATION_TYPES as evaluationType}
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
			<label class="input-wrap">
				<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Points</span>
				<input bind:value={selectedStep.evaluation.points} type="number" class="input text-lg" />
			</label>
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
					{#each selectedStep.player_input.options as option, optionIndex}
						<div class="grid gap-3 md:grid-cols-[1fr_auto]">
							<input
								bind:value={selectedStep.player_input.options[optionIndex]}
								class="input text-lg"
							/>
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
