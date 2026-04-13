<script lang="ts">
	import 'iconify-icon';
	import { getYouTubeMedia } from '$lib/media/youtube.js';
	import { messages } from '$lib/i18n';
	import {
		IMAGE_REVEALS,
		MEDIA_TYPES,
		getEvaluationDetails,
		getInputKindDetails,
		getCheckboxOptionScores,
		getEvaluationDetailsForInputKind,
		getNumberAnswer,
		getOrderingAnswer,
		getStepHealthIssues,
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

	function scrollToSection(sectionId: string) {
		document.getElementById(sectionId)?.scrollIntoView({
			behavior: 'smooth',
			block: 'start'
		});
	}

	function getMediaTypeLabel(mediaType: (typeof MEDIA_TYPES)[number]) {
		if (mediaType === 'image') {
			return 'Image';
		}
		if (mediaType === 'audio') {
			return 'Audio';
		}
		return 'Video';
	}

	function getMediaTypeHelp(mediaType: (typeof MEDIA_TYPES)[number]) {
		if (mediaType === 'image') {
			return $messages.editor.mediaTypeImageHelp;
		}
		if (mediaType === 'audio') {
			return $messages.editor.mediaTypeAudioHelp;
		}
		return $messages.editor.mediaTypeVideoHelp;
	}

	function getPreviewYouTubeEmbed(step: StepDefinition): string | null {
		if (step.media?.type_ !== 'video') {
			return null;
		}
		return (
			getYouTubeMedia(step.media.src, {
				controls: false,
				loop: step.media.loop,
				origin: typeof window !== 'undefined' ? window.location.origin : undefined
			})?.embedUrl ?? null
		);
	}

	function getRevealLabel(revealMode: (typeof IMAGE_REVEALS)[number]) {
		return $messages.editor.imageReveal[revealMode].label;
	}

	const headerActions = $derived<HeaderAction[]>([
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
	<div class="flex flex-wrap items-start justify-between gap-3 px-4 py-3">
		<div>
			<p class="text-sm font-bold uppercase tracking-wide text-slate-500">
				{selectedFlatStep.roundTitle} · {$messages.editor.slide}
				{selectedFlatStep.globalIndex + 1}
			</p>
			<h2 class="label-title text-2xl">{selectedStep.title || $messages.editor.untitledStep}</h2>
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
				title={`${$messages.editor.headerActionLabels.addStepAfter} — Cmd/Ctrl + Shift + A`}
			>
				<iconify-icon icon="fluent:add-16-filled"></iconify-icon>
				{$messages.editor.headerActionLabels.addStepAfter}
			</button>
		</div>
	</div>

	{#if healthIssues.length > 0}
		<div class="flex flex-wrap gap-2 px-4 pb-2">
			{#each healthIssues as issue}
				<span
					class="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold uppercase tracking-[0.16em] text-amber-800"
				>
					<iconify-icon icon={issue.icon}></iconify-icon>
					{issue.label}
				</span>
			{/each}
		</div>
	{/if}

	<div class="min-h-0 flex-1 overflow-y-auto px-4 pb-4 pr-3">
		<div
			class="sticky top-0 z-20 mb-4 overflow-x-auto rounded-[1.75rem] border border-slate-200 bg-white/92 p-2 shadow-sm backdrop-blur"
		>
			<div class="flex min-w-max gap-2">
				{#each sectionNav as section}
					<button
						type="button"
						class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-bold text-slate-700 transition hover:border-sky-300 hover:bg-sky-50"
						onclick={() => scrollToSection(section.id)}
					>
						<iconify-icon icon={section.icon}></iconify-icon>
						{section.label}
					</button>
				{/each}
			</div>
		</div>

		<div class="grid gap-5">
			<section
				id="main-screen"
				class="rounded-[2rem] border border-slate-200 bg-white/85 p-5 shadow-sm"
			>
				<div class="flex items-start gap-3">
					<div
						class="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-100 text-2xl text-sky-700"
					>
						<iconify-icon icon="fluent:desktop-16-filled"></iconify-icon>
					</div>
					<div>
						<h3 class="label-title text-2xl">{$messages.editor.mainScreen}</h3>
						<p class="text-sm text-slate-600">{$messages.editor.mainScreenHelp}</p>
					</div>
				</div>

				<div class="mt-4 grid gap-4">
					<label class="input-wrap">
						<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
							>{$messages.editor.stepTitle}</span
						>
						<input
							bind:value={selectedStep.title}
							class="input text-lg"
							placeholder={$messages.editor.stepTitlePlaceholder}
						/>
					</label>
					<label class="input-wrap">
						<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
							>{$messages.editor.body}</span
						>
						<textarea
							bind:value={selectedStep.body}
							class="input min-h-28 text-lg"
							placeholder={$messages.editor.bodyPlaceholder}
						></textarea>
					</label>
					{#if showAdvancedFields}
						<label class="input-wrap">
							<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
								>{$messages.editor.stepId}</span
							>
							<input bind:value={selectedStep.id} class="input text-lg" />
						</label>
					{/if}
				</div>

				<div class="mt-6 rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-4">
					<div class="flex flex-wrap items-center justify-between gap-3">
						<div>
							<p class="text-lg font-bold text-slate-900">{$messages.editor.questionMedia}</p>
							<p class="text-sm text-slate-600">{$messages.editor.questionMediaHelp}</p>
						</div>
						{#if selectedStep.media}
							<button
								class="btn btn-danger text-sm"
								type="button"
								onclick={() => onRemoveMedia(selectedStep)}
							>
								{$messages.editor.removeMedia}
							</button>
						{:else}
							<button
								class="btn btn-ghost text-sm"
								type="button"
								onclick={() => onAddMedia(selectedStep)}
							>
								{$messages.editor.addMedia}
							</button>
						{/if}
					</div>

					{#if selectedStep.media}
						<div class="mt-4 grid gap-4">
							<div class="grid gap-3 md:grid-cols-3">
								{#each MEDIA_TYPES as mediaType}
									<button
										type="button"
										class={`rounded-[1.35rem] border px-4 py-4 text-left transition ${
											selectedStep.media.type_ === mediaType
												? 'border-sky-300 bg-sky-50 shadow-sm'
												: 'border-slate-200 bg-white hover:border-sky-200 hover:bg-sky-50/50'
										}`}
										onclick={() => onUpdateMediaType(selectedStep, mediaType)}
									>
										<p class="text-base font-bold text-slate-900">{getMediaTypeLabel(mediaType)}</p>
										<p class="mt-1 text-sm text-slate-600">{getMediaTypeHelp(mediaType)}</p>
									</button>
								{/each}
							</div>

							<div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
								<div class="grid gap-4">
									<label class="input-wrap">
										<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
											{$messages.editor.sourceUrl}
										</span>
										<input
											bind:value={selectedStep.media.src}
											class="input text-lg"
											placeholder={selectedStep.media.type_ === 'video'
												? $messages.editor.videoSourceUrlPlaceholder
												: $messages.editor.sourceUrlPlaceholder}
										/>
										{#if selectedStep.media.type_ === 'video'}
											<p class="text-sm text-slate-500">
												{$messages.editor.videoSourceHelp}
											</p>
										{/if}
									</label>

									{#if selectedStep.media.type_ === 'image'}
										<div class="grid gap-3 md:grid-cols-2">
											{#each IMAGE_REVEALS as revealMode}
												<button
													type="button"
													class={`rounded-[1.25rem] border px-4 py-3 text-left transition ${
														selectedStep.media.reveal === revealMode
															? 'border-sky-300 bg-sky-50'
															: 'border-slate-200 bg-white hover:border-sky-200'
													}`}
													onclick={() =>
														selectedStep.media ? (selectedStep.media.reveal = revealMode) : null}
												>
													<p class="text-sm font-bold uppercase tracking-wide text-slate-700">
														{getRevealLabel(revealMode)}
													</p>
													<p class="mt-1 text-sm text-slate-600">
														{$messages.editor.imageReveal[revealMode].description}
													</p>
												</button>
											{/each}
										</div>
									{/if}

									<label
										class="flex items-center justify-between gap-4 rounded-2xl bg-white px-4 py-3"
									>
										<div>
											<p class="text-lg font-bold">{$messages.editor.loopMedia}</p>
											<p class="text-sm text-slate-600">{$messages.editor.loopMediaHelp}</p>
										</div>
										<input bind:checked={selectedStep.media.loop} type="checkbox" class="h-5 w-5" />
									</label>

									<label class="input-wrap">
										<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
											{$messages.editor.uploadFile}
										</span>
										<input
											type="file"
											class="input text-base file:mr-4 file:rounded-xl file:border-0 file:bg-sky-100 file:px-3 file:py-2 file:font-semibold file:text-sky-700"
											onchange={(event) => onUploadMedia(event, selectedStep, selectedStep.id)}
										/>
									</label>

									{#if uploadKey === selectedStep.id}
										<p class="text-sm font-semibold text-sky-700">
											{$messages.editor.uploadingMedia}
										</p>
									{/if}
								</div>

								<div class="rounded-[1.5rem] border border-slate-200 bg-white p-4">
									<p class="text-sm font-bold uppercase tracking-[0.18em] text-slate-500">
										{$messages.common.preview}
									</p>
									{#if selectedStep.media.src}
										{#if selectedStep.media.type_ === 'image'}
											<img
												src={selectedStep.media.src}
												alt={selectedStep.title}
												class="mt-3 max-h-64 w-full rounded-2xl object-cover"
											/>
										{:else if selectedStep.media.type_ === 'audio'}
											<audio class="mt-3 w-full" controls src={selectedStep.media.src}></audio>
										{:else if selectedStep.media.type_ === 'video'}
											{@const youtubeEmbedUrl = getPreviewYouTubeEmbed(selectedStep)}
											{#if youtubeEmbedUrl}
												<iframe
													class="mt-3 aspect-video w-full rounded-2xl border-0"
													src={youtubeEmbedUrl}
													title={`${selectedStep.title || $messages.common.question} video preview`}
													allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
													referrerpolicy="strict-origin-when-cross-origin"
													allowfullscreen
												></iframe>
											{:else}
												<video
													class="mt-3 max-h-64 w-full rounded-2xl"
													controls
													loop={selectedStep.media.loop}
													src={selectedStep.media.src}
												>
													<track kind="captions" />
												</video>
											{/if}
										{/if}
										<p class="mt-3 text-xs text-slate-500">{selectedStep.media.src}</p>
									{:else}
										<p class="mt-3 text-sm text-slate-500">
											{$messages.editor.previewHelp}
										</p>
									{/if}
								</div>
							</div>
						</div>
					{/if}
				</div>
			</section>

			<section
				id="player-answer"
				class="rounded-[2rem] border border-slate-200 bg-white/85 p-5 shadow-sm"
			>
				<div class="flex items-start gap-3">
					<div
						class="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100 text-2xl text-emerald-700"
					>
						<iconify-icon icon="fluent:people-community-16-filled"></iconify-icon>
					</div>
					<div>
						<h3 class="label-title text-2xl">{$messages.editor.howPlayersAnswer}</h3>
						<p class="text-sm text-slate-600">{$messages.editor.howPlayersAnswerHelp}</p>
					</div>
				</div>

				<div class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
					{#each Object.values(inputKindDetails) as details}
						<button
							type="button"
							class={`rounded-[1.5rem] border p-4 text-left transition ${
								selectedStep.player_input.kind === details.kind
									? 'border-sky-300 bg-sky-50 shadow-sm'
									: 'border-slate-200 bg-white hover:border-sky-200 hover:bg-sky-50/50'
							}`}
							onclick={() => onSetPlayerInputKind(selectedStep, details.kind)}
						>
							<div class="flex items-start gap-3">
								<div
									class="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-2xl text-sky-700 shadow-sm"
								>
									<iconify-icon icon={details.icon}></iconify-icon>
								</div>
								<div>
									<p class="text-base font-bold text-slate-900">{details.label}</p>
									<p class="mt-1 text-sm leading-6 text-slate-600">{details.description}</p>
								</div>
							</div>
						</button>
					{/each}
				</div>

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
											bind:value={selectedStep.player_input.prompt}
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
											bind:value={selectedStep.player_input.placeholder}
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
									<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
										>{$messages.editor.minValue}</span
									>
									<input
										bind:value={selectedStep.player_input.min_value}
										type="number"
										class="input text-lg"
									/>
								</label>
								<label class="input-wrap">
									<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
										>{$messages.editor.maxValue}</span
									>
									<input
										bind:value={selectedStep.player_input.max_value}
										type="number"
										class="input text-lg"
									/>
								</label>
								<label class="input-wrap">
									<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
										{$messages.editor.sliderStep}
									</span>
									<input
										bind:value={selectedStep.player_input.step}
										type="number"
										min="0"
										class="input text-lg"
									/>
								</label>
							</div>
						{/if}

						{#if inputDetails.usesOptions}
							<div class="rounded-[1.5rem] border border-slate-200 bg-white p-4">
								<div class="flex flex-wrap items-center justify-between gap-3">
									<div>
										<p class="text-lg font-bold text-slate-900">
											{selectedStep.player_input.kind === 'ordering'
												? $messages.editor.itemsToOrder
												: selectedStep.player_input.kind === 'radio'
													? $messages.editor.answerChoices
													: $messages.editor.selectableAnswers}
										</p>
										<p class="text-sm text-slate-600">
											{selectedStep.player_input.kind === 'ordering'
												? $messages.editor.itemsToOrderHelp
												: $messages.editor.selectableAnswersHelp}
										</p>
									</div>
									<button
										class="btn btn-ghost text-sm"
										type="button"
										onclick={() => onAddInputOption(selectedStep)}
									>
										{$messages.editor.addOption}
									</button>
								</div>

								<div class="mt-4 grid gap-3">
									{#each selectedStep.player_input.options as option, optionIndex}
										<div
											class="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 md:grid-cols-[auto_1fr_auto_auto]"
										>
											<div
												class="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-sm font-bold text-slate-500"
											>
												{optionIndex + 1}
											</div>
											<input
												value={option}
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
													class="flex items-center gap-2 rounded-2xl bg-white px-4 py-3 text-sm font-semibold text-slate-700"
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
													{$messages.editor.correct}
												</label>
											{:else if selectedStep.player_input.kind === 'checkbox' && selectedStep.evaluation.type_ === 'multi_select_weighted'}
												<label class="input-wrap">
													<span class="text-xs font-bold uppercase tracking-wide text-slate-500"
														>{$messages.editor.points}</span
													>
													<input
														class="input w-24 text-lg"
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
											{:else}
												<div></div>
											{/if}
											<button
												class="btn btn-danger text-sm"
												type="button"
												onclick={() => onRemoveInputOption(selectedStep, optionIndex)}
											>
												{$messages.editor.removeOption}
											</button>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				</div>
			</section>

			<section
				id="scoring"
				class="rounded-[2rem] border border-slate-200 bg-white/85 p-5 shadow-sm"
			>
				<div class="flex items-start gap-3">
					<div
						class="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-100 text-2xl text-amber-700"
					>
						<iconify-icon icon="fluent:checkmark-circle-16-filled"></iconify-icon>
					</div>
					<div>
						<h3 class="label-title text-2xl">{$messages.editor.scoringAndCorrectAnswer}</h3>
						<p class="text-sm text-slate-600">{$messages.editor.scoringHelp}</p>
					</div>
				</div>

				<div class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
					{#each availableEvaluationDetails as details}
						<button
							type="button"
							class={`rounded-[1.4rem] border p-4 text-left transition ${
								selectedStep.evaluation.type_ === details.type
									? 'border-amber-300 bg-amber-50 shadow-sm'
									: 'border-slate-200 bg-white hover:border-amber-200 hover:bg-amber-50/50'
							}`}
							onclick={() => onSetEvaluationType(selectedStep, details.type)}
						>
							<div class="flex items-start gap-3">
								<div
									class="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-2xl text-amber-700 shadow-sm"
								>
									<iconify-icon icon={details.icon}></iconify-icon>
								</div>
								<div>
									<p class="text-base font-bold text-slate-900">{details.label}</p>
									<p class="mt-1 text-sm leading-6 text-slate-600">{details.description}</p>
								</div>
							</div>
						</button>
					{/each}
				</div>

				<div class="mt-5 rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-4">
					<div class="flex flex-wrap items-center justify-between gap-4">
						<div>
							<p class="text-lg font-bold text-slate-900">{evaluationDetails.label}</p>
							<p class="text-sm text-slate-600">{evaluationDetails.description}</p>
						</div>
						{#if selectedStep.evaluation.type_ !== 'multi_select_weighted' && selectedStep.evaluation.type_ !== 'none'}
							<label class="input-wrap min-w-32">
								<span class="text-xs font-bold uppercase tracking-wide text-slate-500"
									>{$messages.editor.points}</span
								>
								<input
									bind:value={selectedStep.evaluation.points}
									type="number"
									class="input text-lg"
								/>
							</label>
						{/if}
					</div>

					<div class="mt-4">
						{#if selectedStep.evaluation.type_ === 'ordering_match'}
							<div class="grid gap-3">
								<p class="text-sm font-semibold text-slate-700">
									{$messages.editor.correctOrderHelp}
								</p>
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
												onSetOrderingAnswer(
													selectedStep,
													optionIndex,
													(event.currentTarget as HTMLInputElement).value
												)}
										/>
									</label>
								{/each}
							</div>
						{:else if selectedStep.evaluation.type_ === 'exact_number' || selectedStep.evaluation.type_ === 'closest_number'}
							<div class="grid gap-3 md:grid-cols-[minmax(0,1fr)_12rem]">
								<label class="input-wrap">
									<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
										{$messages.editor.correctNumber}
									</span>
									<input
										class="input text-lg"
										type="number"
										value={getNumberAnswer(selectedStep)}
										oninput={(event) =>
											(selectedStep.evaluation.answer = (
												event.currentTarget as HTMLInputElement
											).value)}
									/>
								</label>
								<div
									class="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600"
								>
									<p class="font-bold text-slate-900">{$messages.editor.scoringSummary}</p>
									<p class="mt-2">
										{selectedStep.evaluation.type_ === 'exact_number'
											? $messages.editor.exactNumberSummary
											: $messages.editor.closestNumberSummary}
									</p>
								</div>
							</div>
						{:else if selectedStep.evaluation.type_ === 'multi_select_weighted'}
							<div class="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
								<p class="font-bold text-slate-900">{$messages.editor.configureScoresAbove}</p>
								<p class="mt-2">{$messages.editor.configurePointsAboveHelp}</p>
							</div>
						{:else if selectedStep.evaluation.type_ === 'exact_text' && selectedStep.player_input.kind === 'radio'}
							<div class="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
								<p class="font-bold text-slate-900">{$messages.editor.markCorrectOption}</p>
								<p class="mt-2">{$messages.editor.markCorrectOptionHelp}</p>
							</div>
						{:else if selectedStep.evaluation.type_ === 'host_judged'}
							<div class="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
								<p class="font-bold text-slate-900">{$messages.editor.hostDecidesCorrectness}</p>
								<p class="mt-2">{$messages.editor.hostReviewedHelp}</p>
							</div>
						{:else if selectedStep.evaluation.type_ !== 'none'}
							<label class="input-wrap">
								<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
									{$messages.editor.correctAnswerRubric}
								</span>
								<input
									class="input text-lg"
									value={getTextAnswer(selectedStep)}
									placeholder={$messages.editor.expectedAnswerPlaceholder}
									oninput={(event) =>
										(selectedStep.evaluation.answer = (
											event.currentTarget as HTMLInputElement
										).value)}
								/>
							</label>
						{:else}
							<div class="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
								<p class="font-bold text-slate-900">{$messages.editor.noAnswerRequired}</p>
								<p class="mt-2">{$messages.editor.displayOnlyHelp}</p>
							</div>
						{/if}
					</div>
				</div>
			</section>

			<section id="timer" class="rounded-[2rem] border border-slate-200 bg-white/85 p-5 shadow-sm">
				<div class="flex items-start gap-3">
					<div
						class="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-100 text-2xl text-violet-700"
					>
						<iconify-icon icon="fluent:timer-16-filled"></iconify-icon>
					</div>
					<div>
						<h3 class="label-title text-2xl">{$messages.editor.timer}</h3>
						<p class="text-sm text-slate-600">{$messages.editor.timerHelp}</p>
					</div>
				</div>

				<div class="mt-4 grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
					<label class="input-wrap">
						<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
							>{$messages.editor.timerSeconds}</span
						>
						<input
							bind:value={selectedStep.timer.seconds}
							type="number"
							min="0"
							class="input text-lg"
						/>
					</label>
					<label
						class="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
					>
						<div>
							<p class="text-lg font-bold">{$messages.editor.enforcedTimer}</p>
							<p class="text-sm text-slate-600">{$messages.editor.enforcedTimerHelp}</p>
						</div>
						<input bind:checked={selectedStep.timer.enforced} type="checkbox" class="h-5 w-5" />
					</label>
				</div>
			</section>

			<section
				id="host-controls"
				class="rounded-[2rem] border border-slate-200 bg-white/85 p-5 shadow-sm"
			>
				<div class="flex items-start gap-3">
					<div
						class="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-rose-100 text-2xl text-rose-700"
					>
						<iconify-icon icon="fluent:person-settings-16-filled"></iconify-icon>
					</div>
					<div>
						<h3 class="label-title text-2xl">{$messages.editor.hostControls}</h3>
						<p class="text-sm text-slate-600">{$messages.editor.hostControlsHelp}</p>
					</div>
				</div>

				<div class="mt-4 grid gap-3 md:grid-cols-3">
					<label
						class="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
					>
						<div>
							<p class="text-sm font-semibold text-slate-900">{$messages.editor.revealAnswers}</p>
							<p class="text-xs text-slate-600">{$messages.editor.revealAnswersHelp}</p>
						</div>
						<input
							bind:checked={selectedStep.host_behavior.reveal_answers}
							type="checkbox"
							class="h-5 w-5"
						/>
					</label>
					<label
						class="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
					>
						<div>
							<p class="text-sm font-semibold text-slate-900">{$messages.editor.showSubmissions}</p>
							<p class="text-xs text-slate-600">{$messages.editor.showSubmissionsHelp}</p>
						</div>
						<input
							bind:checked={selectedStep.host_behavior.show_submissions}
							type="checkbox"
							class="h-5 w-5"
						/>
					</label>
					<label
						class="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
					>
						<div>
							<p class="text-sm font-semibold text-slate-900">{$messages.editor.customPoints}</p>
							<p class="text-xs text-slate-600">{$messages.editor.customPointsHelp}</p>
						</div>
						<input
							bind:checked={selectedStep.host_behavior.allow_custom_points}
							type="checkbox"
							class="h-5 w-5"
						/>
					</label>
				</div>
			</section>
		</div>
	</div>
</section>
