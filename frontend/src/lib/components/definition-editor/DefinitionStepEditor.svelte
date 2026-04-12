<script lang="ts">
	import 'iconify-icon';
	import { getYouTubeMedia } from '$lib/media/youtube.js';
	import {
		EVALUATION_DETAILS,
		IMAGE_REVEALS,
		INPUT_KIND_DETAILS,
		MEDIA_TYPES,
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

	const inputDetails = $derived(INPUT_KIND_DETAILS[selectedStep.player_input.kind]);
	const availableEvaluationDetails = $derived(
		getEvaluationDetailsForInputKind(selectedStep.player_input.kind)
	);
	const evaluationDetails = $derived(EVALUATION_DETAILS[selectedStep.evaluation.type_]);
	const checkboxOptionScores = $derived(getCheckboxOptionScores(selectedStep));
	const healthIssues = $derived(getStepHealthIssues(selectedStep));
	const orderedAnswer = $derived(getOrderingAnswer(selectedStep));
	const sectionNav = [
		{
			id: 'main-screen',
			label: 'Main Screen',
			icon: 'fluent:desktop-16-filled'
		},
		{
			id: 'player-answer',
			label: 'How Players Answer',
			icon: 'fluent:people-community-16-filled'
		},
		{
			id: 'scoring',
			label: 'Scoring',
			icon: 'fluent:checkmark-circle-16-filled'
		},
		{
			id: 'timer',
			label: 'Timer',
			icon: 'fluent:timer-16-filled'
		},
		{
			id: 'host-controls',
			label: 'Host Controls',
			icon: 'fluent:person-settings-16-filled'
		}
	];

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
		return mediaType.charAt(0).toUpperCase() + mediaType.slice(1);
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
		return revealMode.replaceAll('_', ' ');
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

<section class="flex h-full min-h-0 flex-col bg-white/70">
	<div class="flex flex-wrap items-start justify-between gap-3 px-4 py-3">
		<div>
			<p class="text-sm font-bold uppercase tracking-wide text-slate-500">
				{selectedFlatStep.roundTitle} · Slide {selectedFlatStep.globalIndex + 1}
			</p>
			<h2 class="label-title text-2xl">{selectedStep.title || 'Untitled Step'}</h2>
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
						<h3 class="label-title text-2xl">Main Screen</h3>
						<p class="text-sm text-slate-600">
							Everything the audience sees first: question text, supporting copy, and media.
						</p>
					</div>
				</div>

				<div class="mt-4 grid gap-4">
					<label class="input-wrap">
						<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Title</span>
						<input
							bind:value={selectedStep.title}
							class="input text-lg"
							placeholder="Question title"
						/>
					</label>
					<label class="input-wrap">
						<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Body</span>
						<textarea
							bind:value={selectedStep.body}
							class="input min-h-28 text-lg"
							placeholder="Optional supporting text on the big screen"
						></textarea>
					</label>
					{#if showAdvancedFields}
						<label class="input-wrap">
							<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Step id</span>
							<input bind:value={selectedStep.id} class="input text-lg" />
						</label>
					{/if}
				</div>

				<div class="mt-6 rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-4">
					<div class="flex flex-wrap items-center justify-between gap-3">
						<div>
							<p class="text-lg font-bold text-slate-900">Question media</p>
							<p class="text-sm text-slate-600">
								Add an image, audio clip, or video to support the question on the main screen.
							</p>
						</div>
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
										<p class="mt-1 text-sm text-slate-600">
											{mediaType === 'image'
												? 'Reveal a still image on the main screen.'
												: mediaType === 'audio'
													? 'Play an audio clue or sound effect.'
													: 'Show a video clip during the step.'}
										</p>
									</button>
								{/each}
							</div>

							<div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
								<div class="grid gap-4">
									<label class="input-wrap">
										<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
											Source URL
										</span>
										<input
											bind:value={selectedStep.media.src}
											class="input text-lg"
											placeholder={selectedStep.media.type_ === 'video'
												? '/api/v1/media/... or https://youtu.be/...'
												: '/api/v1/media/...'}
										/>
										{#if selectedStep.media.type_ === 'video'}
											<p class="text-sm text-slate-500">
												Use a direct video URL, an uploaded file, or a YouTube link.
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
														{revealMode === 'none'
															? 'Show the image as-is.'
															: revealMode === 'blur_to_clear'
																? 'Start blurred and sharpen over time.'
																: revealMode === 'blur_circle'
																	? 'Reveal the image through a moving spotlight.'
																	: 'Start zoomed in and pull back.'}
													</p>
												</button>
											{/each}
										</div>
									{/if}

									<label
										class="flex items-center justify-between gap-4 rounded-2xl bg-white px-4 py-3"
									>
										<div>
											<p class="text-lg font-bold">Loop media</p>
											<p class="text-sm text-slate-600">
												Useful for short ambient clips and repeatable audio.
											</p>
										</div>
										<input bind:checked={selectedStep.media.loop} type="checkbox" class="h-5 w-5" />
									</label>

									<label class="input-wrap">
										<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
											Upload file
										</span>
										<input
											type="file"
											class="input text-base file:mr-4 file:rounded-xl file:border-0 file:bg-sky-100 file:px-3 file:py-2 file:font-semibold file:text-sky-700"
											onchange={(event) => onUploadMedia(event, selectedStep, selectedStep.id)}
										/>
									</label>

									{#if uploadKey === selectedStep.id}
										<p class="text-sm font-semibold text-sky-700">Uploading media...</p>
									{/if}
								</div>

								<div class="rounded-[1.5rem] border border-slate-200 bg-white p-4">
									<p class="text-sm font-bold uppercase tracking-[0.18em] text-slate-500">
										Preview
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
													title={`${selectedStep.title || 'Question'} video preview`}
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
											Add a media URL or upload a file to preview it here.
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
						<h3 class="label-title text-2xl">How Players Answer</h3>
						<p class="text-sm text-slate-600">
							Choose the interaction first, then configure the prompt and any options players will
							see.
						</p>
					</div>
				</div>

				<div class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
					{#each Object.values(INPUT_KIND_DETAILS) as details}
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
							Recommended scoring: {EVALUATION_DETAILS[inputDetails.recommendedEvaluation].label}
						</span>
					</div>

					<div class="mt-4 grid gap-4">
						{#if inputDetails.usesPrompt || inputDetails.usesPlaceholder}
							<div class="grid gap-4 md:grid-cols-2">
								{#if inputDetails.usesPrompt}
									<label class="input-wrap">
										<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
											Input prompt
										</span>
										<input
											bind:value={selectedStep.player_input.prompt}
											class="input text-lg"
											placeholder="What should players do?"
										/>
									</label>
								{/if}
								{#if inputDetails.usesPlaceholder}
									<label class="input-wrap">
										<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
											Placeholder
										</span>
										<input
											bind:value={selectedStep.player_input.placeholder}
											class="input text-lg"
											placeholder="Optional helper text inside the input"
										/>
									</label>
								{/if}
							</div>
						{/if}

						{#if inputDetails.usesNumericRange}
							<div class="grid gap-3 md:grid-cols-3">
								<label class="input-wrap">
									<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
										>Min value</span
									>
									<input
										bind:value={selectedStep.player_input.min_value}
										type="number"
										class="input text-lg"
									/>
								</label>
								<label class="input-wrap">
									<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
										>Max value</span
									>
									<input
										bind:value={selectedStep.player_input.max_value}
										type="number"
										class="input text-lg"
									/>
								</label>
								<label class="input-wrap">
									<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
										Slider step
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
												? 'Items to order'
												: selectedStep.player_input.kind === 'radio'
													? 'Answer choices'
													: 'Selectable answers'}
										</p>
										<p class="text-sm text-slate-600">
											{selectedStep.player_input.kind === 'ordering'
												? 'These are the items players will arrange.'
												: 'These are the options players can choose from.'}
										</p>
									</div>
									<button
										class="btn btn-ghost text-sm"
										type="button"
										onclick={() => onAddInputOption(selectedStep)}
									>
										Add Option
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
													Correct
												</label>
											{:else if selectedStep.player_input.kind === 'checkbox' && selectedStep.evaluation.type_ === 'multi_select_weighted'}
												<label class="input-wrap">
													<span class="text-xs font-bold uppercase tracking-wide text-slate-500"
														>Points</span
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
												Remove
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
						<h3 class="label-title text-2xl">Scoring & Correct Answer</h3>
						<p class="text-sm text-slate-600">
							Pick how this step is judged, then set the answer or scoring rules players should
							match.
						</p>
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
								<span class="text-xs font-bold uppercase tracking-wide text-slate-500">Points</span>
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
									Set the correct order players should end up with.
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
										Correct number
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
									<p class="font-bold text-slate-900">Scoring summary</p>
									<p class="mt-2">
										{selectedStep.evaluation.type_ === 'exact_number'
											? 'Only the exact number scores.'
											: 'Nearest numeric answer wins the points.'}
									</p>
								</div>
							</div>
						{:else if selectedStep.evaluation.type_ === 'multi_select_weighted'}
							<div class="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
								<p class="font-bold text-slate-900">Configure scores in the option list above</p>
								<p class="mt-2">
									Each checked option awards its configured points. Negative values subtract points.
								</p>
							</div>
						{:else if selectedStep.evaluation.type_ === 'exact_text' && selectedStep.player_input.kind === 'radio'}
							<div class="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
								<p class="font-bold text-slate-900">Mark the correct option in the answer list</p>
								<p class="mt-2">Use the “Correct” radio control beside the right answer choice.</p>
							</div>
						{:else if selectedStep.evaluation.type_ === 'host_judged'}
							<div class="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
								<p class="font-bold text-slate-900">Host decides correctness live</p>
								<p class="mt-2">
									Submissions are reviewed by the host during the game, so no exact answer is
									required here.
								</p>
							</div>
						{:else if selectedStep.evaluation.type_ !== 'none'}
							<label class="input-wrap">
								<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
									Correct answer / rubric
								</span>
								<input
									class="input text-lg"
									value={getTextAnswer(selectedStep)}
									placeholder="Enter the expected answer"
									oninput={(event) =>
										(selectedStep.evaluation.answer = (
											event.currentTarget as HTMLInputElement
										).value)}
								/>
							</label>
						{:else}
							<div class="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
								<p class="font-bold text-slate-900">No answer required</p>
								<p class="mt-2">
									This step is display-only or reviewed outside the automatic scoring flow.
								</p>
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
						<h3 class="label-title text-2xl">Timer</h3>
						<p class="text-sm text-slate-600">
							Set the pace of the question and decide whether the step should close automatically.
						</p>
					</div>
				</div>

				<div class="mt-4 grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
					<label class="input-wrap">
						<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
							>Timer seconds</span
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
							<p class="text-lg font-bold">Enforced timer</p>
							<p class="text-sm text-slate-600">
								Automatically close the step when the countdown reaches zero.
							</p>
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
						<h3 class="label-title text-2xl">Host Controls</h3>
						<p class="text-sm text-slate-600">
							Decide what the host can reveal and how much manual control they keep during play.
						</p>
					</div>
				</div>

				<div class="mt-4 grid gap-3 md:grid-cols-3">
					<label
						class="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
					>
						<div>
							<p class="text-sm font-semibold text-slate-900">Reveal answers</p>
							<p class="text-xs text-slate-600">Allow the host to reveal the answer on screen.</p>
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
							<p class="text-sm font-semibold text-slate-900">Show submissions</p>
							<p class="text-xs text-slate-600">Let the host inspect player answers live.</p>
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
							<p class="text-sm font-semibold text-slate-900">Custom points</p>
							<p class="text-xs text-slate-600">
								Enable manual point overrides from the host view.
							</p>
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
