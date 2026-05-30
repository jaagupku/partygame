<script lang="ts">
	import { getDrawingVoteRubric } from '$lib/drawing-vote.js';
	import { messages } from '$lib/i18n';
	import DrawingDisplay from '$lib/components/DrawingDisplay.svelte';
	import DrawingInput from '$lib/components/DrawingInput.svelte';
	import { triggerBuzzerHapticPulse } from '$lib/haptics.js';
	import MapPointEditor from '$lib/components/MapPointEditor.svelte';
	import OrderingList from '$lib/components/OrderingList.svelte';

	interface PlayerInputPanelProps {
		activeStep?: RuntimeStepState;
		baseInputDisabled: boolean;
		buzzerActive: boolean;
		canContinueHostlessInfoSlide: boolean;
		disabledBuzzerPlayerIds: string[];
		drawingItems: DrawingVoteItem[];
		ownDrawingId?: string;
		drawingVotedPlayerIds: string[];
		hasSubmitted: boolean;
		playerId: string;
		mode?: 'live' | 'preview';
		onContinueInfoSlide: () => void;
		onSubmitAnswer: (value: unknown) => void;
		onSubmitDrawingVote: (drawingId: string) => void;
	}

	let {
		activeStep,
		baseInputDisabled,
		buzzerActive,
		canContinueHostlessInfoSlide,
		disabledBuzzerPlayerIds,
		drawingItems,
		ownDrawingId,
		drawingVotedPlayerIds,
		hasSubmitted,
		playerId,
		mode = 'live',
		onContinueInfoSlide,
		onSubmitAnswer,
		onSubmitDrawingVote
	}: PlayerInputPanelProps = $props();

	let answerValue = $state<string | number>('');
	let orderingItems = $state<string[]>([]);
	let selectedRadioOption = $state<string | null>(null);
	let selectedCheckboxOptions = $state<string[]>([]);
	let selectedMapPoint = $state<MapPoint | null>(null);
	let pendingDrawingVoteId = $state<string | undefined>(undefined);
	let orderingStepId = $state<string | undefined>(undefined);
	let inputStepId = $state<string | undefined>(undefined);
	let pendingSubmissionStepId = $state<string | undefined>(undefined);

	const inputDisabled = $derived(baseInputDisabled || pendingSubmissionStepId === activeStep?.id);
	const buzzerLockedOut = $derived(disabledBuzzerPlayerIds.includes(playerId));
	const useNumberSlider = $derived(hasConfiguredNumberSlider(activeStep));
	const drawingVoteSubmitted = $derived(drawingVotedPlayerIds.includes(playerId));
	const visibleDrawingItems = $derived(drawingItems.filter((item) => item.id !== ownDrawingId));
	const drawingVoteRubric = $derived(getDrawingVoteRubric(activeStep));
	const previewMode = $derived(mode === 'preview');
	const drawingVoteDisabled = $derived(
		baseInputDisabled || previewMode || drawingVoteSubmitted || Boolean(pendingDrawingVoteId)
	);

	$effect(() => {
		const step = activeStep;
		if (step?.id !== inputStepId) {
			answerValue = hasConfiguredNumberSlider(step) ? step.slider_min : '';
			selectedRadioOption = null;
			selectedCheckboxOptions = [];
			selectedMapPoint = null;
			pendingDrawingVoteId = undefined;
			inputStepId = step?.id;
			pendingSubmissionStepId = undefined;
		}
		if (step?.input_kind !== 'ordering') {
			orderingItems = [];
			orderingStepId = undefined;
			return;
		}
		if (orderingStepId === step.id) {
			return;
		}
		orderingStepId = step.id;
		orderingItems = [...step.input_options];
	});

	$effect(() => {
		if (hasSubmitted) {
			pendingSubmissionStepId = undefined;
		}
	});

	$effect(() => {
		if (drawingVoteSubmitted) {
			pendingDrawingVoteId = undefined;
		}
	});

	function submitAnswer() {
		const step = activeStep;
		if (!step || inputDisabled || previewMode) {
			return;
		}
		let value: unknown = answerValue;
		if (step.input_kind === 'number') {
			value = Number(answerValue);
		} else if (step.input_kind === 'ordering') {
			value = orderingItems;
		} else if (step.input_kind === 'radio') {
			value = selectedRadioOption;
		} else if (step.input_kind === 'checkbox') {
			value = selectedCheckboxOptions;
		} else if (step.input_kind === 'map') {
			value = selectedMapPoint;
		} else if (step.input_kind === 'text') {
			value = String(answerValue);
		}

		pendingSubmissionStepId = step.id;
		onSubmitAnswer(value);
	}

	function buzz() {
		if (inputDisabled || previewMode || buzzerLockedOut || !buzzerActive) {
			return;
		}
		triggerBuzzerHapticPulse();
		pendingSubmissionStepId = activeStep?.id;
		onSubmitAnswer('buzz');
	}

	function submitDrawing(drawing: DrawingSubmission) {
		const step = activeStep;
		if (!step || inputDisabled || previewMode) {
			return;
		}
		pendingSubmissionStepId = step.id;
		onSubmitAnswer(drawing);
	}

	function submitRadioOption(option: string) {
		selectedRadioOption = option;
		answerValue = option;
		if (!previewMode) {
			submitAnswer();
		}
	}

	function toggleCheckboxOption(option: string) {
		if (selectedCheckboxOptions.includes(option)) {
			selectedCheckboxOptions = selectedCheckboxOptions.filter((entry) => entry !== option);
			return;
		}
		selectedCheckboxOptions = [...selectedCheckboxOptions, option];
	}

	function hasConfiguredNumberSlider(
		step: RuntimeStepState | undefined
	): step is RuntimeStepState & { slider_min: number; slider_max: number; slider_step: number } {
		return (
			step?.input_kind === 'number' &&
			step.slider_min !== undefined &&
			step.slider_min !== null &&
			step.slider_max !== undefined &&
			step.slider_max !== null &&
			step.slider_step !== undefined &&
			step.slider_step !== null
		);
	}

	function submitDrawingVote(drawingId: string) {
		if (drawingVoteDisabled) {
			return;
		}
		pendingDrawingVoteId = drawingId;
		onSubmitDrawingVote(drawingId);
	}
</script>

{#if activeStep?.input_kind === 'drawing' && activeStep.evaluation_type === 'favorite_vote' && activeStep.input_enabled && drawingItems.length > 0}
	<section class="card controller-compact-card stack-md">
		<h2 class="label-title text-2xl">{$messages.gameplay.voteForFavoriteDrawing}</h2>
		<p class="text-sm text-slate-600">
			{drawingVoteSubmitted
				? $messages.gameplay.drawingVoteSubmitted
				: $messages.gameplay.pickFavoriteDrawing}
		</p>
		{#if drawingVoteRubric}
			<div class="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3">
				<p class="text-xs font-black uppercase tracking-wide text-sky-700">
					{$messages.gameplay.drawingVoteRubric}
				</p>
				<p class="mt-1 text-sm font-bold leading-snug text-slate-900">{drawingVoteRubric}</p>
			</div>
		{/if}
		{#if visibleDrawingItems.length > 0}
			<div class="grid gap-3 sm:grid-cols-2">
				{#each visibleDrawingItems as item}
					<button
						type="button"
						class={`drawing-vote-card ${pendingDrawingVoteId === item.id ? 'drawing-vote-card-selected' : ''}`}
						disabled={drawingVoteDisabled}
						onclick={() => submitDrawingVote(item.id)}
					>
						<DrawingDisplay drawing={item.value} />
						<span>{item.label}</span>
					</button>
				{/each}
			</div>
		{:else}
			<p class="rounded-2xl bg-slate-100 px-4 py-3 text-sm font-semibold text-slate-600">
				{$messages.gameplay.noOtherDrawingsToVote}
			</p>
		{/if}
	</section>
{:else if activeStep?.input_kind === 'buzzer'}
	<section class="card controller-compact-card stack-md text-center">
		<h2 class="label-title text-2xl">{$messages.gameplay.buzzer}</h2>
		<p>
			{inputDisabled
				? hasSubmitted
					? $messages.gameplay.answerReceivedWaiting
					: $messages.gameplay.stepClosed
				: buzzerLockedOut
					? $messages.gameplay.buzzerChanceUsed
					: buzzerActive
						? $messages.gameplay.buzzNow
						: $messages.gameplay.waitForHost}
		</p>
		<button
			type="button"
			disabled={inputDisabled || previewMode || !buzzerActive || buzzerLockedOut}
			class="btn btn-accent text-4xl"
			onclick={buzz}
		>
			{$messages.gameplay.buzzer}
		</button>
	</section>
{:else if activeStep?.input_kind === 'text'}
	<section class="card controller-compact-card stack-md">
		<h2 class="label-title text-2xl">{$messages.gameplay.yourAnswer}</h2>
		{#if inputDisabled}
			<p class="text-sm text-slate-600">
				{hasSubmitted
					? $messages.gameplay.answerSubmitted
					: $messages.gameplay.stepClosedAnswersDisabled}
			</p>
		{/if}
		<button
			type="button"
			class="btn btn-primary"
			onclick={submitAnswer}
			disabled={inputDisabled || previewMode}
		>
			{$messages.gameplay.submitAnswer}
		</button>
		<input
			class="input"
			type="text"
			bind:value={answerValue}
			disabled={inputDisabled}
			placeholder={activeStep?.input_placeholder ?? $messages.gameplay.typeYourAnswer}
		/>
	</section>
{:else if activeStep?.input_kind === 'number'}
	<section class="card controller-compact-card stack-md">
		<h2 class="label-title text-2xl">{$messages.gameplay.yourAnswer}</h2>
		{#if inputDisabled}
			<p class="text-sm text-slate-600">
				{hasSubmitted
					? $messages.gameplay.answerSubmitted
					: $messages.gameplay.stepClosedAnswersDisabled}
			</p>
		{/if}
		<button
			type="button"
			class="btn btn-primary"
			onclick={submitAnswer}
			disabled={inputDisabled || previewMode}
		>
			{$messages.gameplay.submitAnswer}
		</button>
		{#if useNumberSlider}
			<div class="stack-md">
				<div class="flex items-center justify-between gap-4">
					<span class="text-sm font-bold text-slate-600">{activeStep?.slider_min}</span>
					<output class="rounded-2xl border bg-white px-5 py-2 text-center text-3xl font-extrabold">
						{answerValue}
					</output>
					<span class="text-sm font-bold text-slate-600">{activeStep?.slider_max}</span>
				</div>
				<input
					class="number-slider"
					type="range"
					min={activeStep?.slider_min}
					max={activeStep?.slider_max}
					step={activeStep?.slider_step}
					bind:value={answerValue}
					disabled={inputDisabled}
				/>
			</div>
		{:else}
			<input
				class="input"
				type="number"
				min={activeStep?.slider_min}
				max={activeStep?.slider_max}
				step={activeStep?.slider_step ?? 1}
				bind:value={answerValue}
				disabled={inputDisabled}
				placeholder={activeStep?.input_placeholder ?? $messages.gameplay.enterNumber}
			/>
		{/if}
	</section>
{:else if activeStep?.input_kind === 'ordering'}
	<section class="card controller-compact-card stack-md">
		<h2 class="label-title text-2xl">{$messages.gameplay.orderingAnswer}</h2>
		<p class="text-sm text-slate-600">
			{inputDisabled
				? hasSubmitted
					? $messages.gameplay.orderSubmitted
					: $messages.gameplay.reorderingDisabled
				: $messages.gameplay.dragOrTapItemsToOrder}
		</p>
		<button
			type="button"
			class="btn btn-primary"
			onclick={submitAnswer}
			disabled={inputDisabled || previewMode}
		>
			{$messages.gameplay.submitOrder}
		</button>
		<OrderingList
			items={orderingItems}
			disabled={inputDisabled}
			dragLabel={$messages.gameplay.dragOrderItem}
			moveUpLabel={$messages.gameplay.moveOrderItemUp}
			moveDownLabel={$messages.gameplay.moveOrderItemDown}
			onReorder={(items) => (orderingItems = items)}
		/>
	</section>
{:else if activeStep?.input_kind === 'radio'}
	<section class="card controller-compact-card stack-md">
		<h2 class="label-title text-2xl">{$messages.gameplay.chooseOne}</h2>
		<p class="text-sm text-slate-600">
			{inputDisabled
				? hasSubmitted
					? $messages.gameplay.choiceLocked
					: $messages.gameplay.newSelectionsDisabled
				: $messages.gameplay.tapOneOption}
		</p>
		<div class="grid gap-3">
			{#each activeStep.input_options as option}
				<button
					type="button"
					class={`btn justify-start text-left text-xl ${
						selectedRadioOption === option ? 'btn-primary text-white' : 'btn-ghost'
					}`}
					disabled={inputDisabled}
					onclick={() => submitRadioOption(option)}
				>
					{option}
				</button>
			{/each}
		</div>
	</section>
{:else if activeStep?.input_kind === 'checkbox'}
	<section class="card controller-compact-card stack-md">
		<h2 class="label-title text-2xl">{$messages.gameplay.chooseOneOrMore}</h2>
		<p class="text-sm text-slate-600">
			{inputDisabled
				? hasSubmitted
					? $messages.gameplay.selectionSubmitted
					: $messages.gameplay.newSelectionsDisabled
				: $messages.gameplay.tapOptionsThenSubmit}
		</p>
		<button
			type="button"
			class="btn btn-primary"
			onclick={submitAnswer}
			disabled={inputDisabled || previewMode || selectedCheckboxOptions.length === 0}
		>
			{$messages.gameplay.submitSelection}
		</button>
		<div class="grid gap-3">
			{#each activeStep.input_options as option}
				<button
					type="button"
					class={`btn justify-start text-left text-xl ${
						selectedCheckboxOptions.includes(option) ? 'btn-primary text-white' : 'btn-ghost'
					}`}
					disabled={inputDisabled}
					onclick={() => toggleCheckboxOption(option)}
				>
					{option}
				</button>
			{/each}
		</div>
	</section>
{:else if activeStep?.input_kind === 'map'}
	<section class="card controller-compact-card map-answer-card">
		<div class="controller-action-row">
			<div class="min-w-0">
				<h2 class="label-title text-2xl">{$messages.gameplay.mapAnswer}</h2>
				<p class="controller-input-help text-sm text-slate-600">
					{inputDisabled
						? hasSubmitted
							? $messages.gameplay.mapGuessSubmitted
							: $messages.gameplay.stepClosedAnswersDisabled
						: $messages.gameplay.tapMapToGuess}
				</p>
			</div>
			<button
				type="button"
				class="btn btn-primary controller-primary-action"
				onclick={submitAnswer}
				disabled={inputDisabled || previewMode || !selectedMapPoint}
			>
				{$messages.gameplay.submitMapGuess}
			</button>
		</div>
		{#if activeStep.map}
			<MapPointEditor
				mode="player"
				mapConfig={activeStep.map}
				selectedPoint={selectedMapPoint}
				editablePoint={!inputDisabled}
				heightClass="controller-map-height"
				resetViewKey={activeStep.id}
				onPointChange={(point) => (selectedMapPoint = point)}
			/>
		{/if}
	</section>
{:else if activeStep?.input_kind === 'drawing'}
	<section class="card controller-compact-card drawing-answer-card stack-md">
		<h2 class="label-title text-2xl">{$messages.gameplay.drawingAnswer}</h2>
		<p class="text-sm text-slate-600">
			{inputDisabled
				? hasSubmitted
					? $messages.gameplay.drawingSubmitted
					: $messages.gameplay.stepClosedAnswersDisabled
				: $messages.gameplay.drawYourAnswer}
		</p>
		<div class="drawing-input-fill">
			<DrawingInput disabled={inputDisabled} {mode} submitPosition="top" onSubmit={submitDrawing} />
		</div>
	</section>
{:else}
	<section class="card controller-compact-card text-center">
		<p class="text-lg">{$messages.gameplay.noPhoneInput}</p>
		{#if canContinueHostlessInfoSlide}
			<p class="mt-2 text-slate-600">{$messages.gameplay.youCanContinueInfoSlide}</p>
			<button
				type="button"
				class="btn btn-primary mt-4"
				onclick={onContinueInfoSlide}
				disabled={previewMode}
			>
				{$messages.gameplay.advanceStep}
			</button>
		{/if}
	</section>
{/if}

<style>
	.map-answer-card {
		flex: 1;
		display: flex;
		min-height: 0;
		flex-direction: column;
		gap: 0.65rem;
		padding: 0.6rem;
	}

	.drawing-answer-card {
		min-height: 0;
		gap: 0.55rem;
	}

	.drawing-input-fill {
		min-height: 0;
	}

	.drawing-vote-card {
		display: grid;
		gap: 0.65rem;
		border-radius: 1rem;
		border: 2px solid rgb(226 232 240);
		background: rgb(255 255 255 / 0.82);
		padding: 0.7rem;
		text-align: left;
		font-weight: 900;
		color: rgb(15 23 42);
		transition:
			border-color 150ms ease,
			transform 150ms ease,
			box-shadow 150ms ease;
	}

	.drawing-vote-card:not(:disabled):hover {
		transform: translateY(-1px);
		border-color: rgb(59 130 246);
		box-shadow: 0 12px 24px rgb(15 23 42 / 0.12);
	}

	.drawing-vote-card-selected {
		border-color: rgb(37 99 235);
		background: rgb(239 246 255);
	}

	.number-slider {
		appearance: none;
		width: 100%;
		min-height: 3.5rem;
		background: transparent;
	}

	.number-slider::-webkit-slider-runnable-track {
		height: 0.85rem;
		border-radius: 999px;
		background: linear-gradient(140deg, var(--party-primary), var(--party-primary-strong));
	}

	.number-slider::-moz-range-track {
		height: 0.85rem;
		border-radius: 999px;
		background: linear-gradient(140deg, var(--party-primary), var(--party-primary-strong));
	}

	.number-slider::-webkit-slider-thumb {
		appearance: none;
		width: 2.75rem;
		height: 2.75rem;
		margin-top: -0.95rem;
		border: 4px solid white;
		border-radius: 999px;
		background: var(--party-accent);
		box-shadow: 0 8px 18px rgba(15, 23, 42, 0.18);
	}

	.number-slider::-moz-range-thumb {
		width: 2.35rem;
		height: 2.35rem;
		border: 4px solid white;
		border-radius: 999px;
		background: var(--party-accent);
		box-shadow: 0 8px 18px rgba(15, 23, 42, 0.18);
	}

	.number-slider:focus-visible {
		outline: 4px solid rgba(14, 165, 233, 0.24);
		outline-offset: 0.25rem;
		border-radius: 999px;
	}

	.number-slider:disabled {
		opacity: 0.5;
	}

	:global(.controller-map-height) {
		height: clamp(18rem, calc(100dvh - 15rem), 44rem);
		min-height: 18rem;
	}

	@media (max-width: 640px) {
		.controller-input-help {
			margin-top: 0.1rem;
			font-size: 0.82rem;
			line-height: 1.2;
		}

		.map-answer-card :global(.map-shell) {
			flex: 1;
			height: auto;
			min-height: 18rem;
			border-radius: 0.75rem;
		}

		.drawing-answer-card {
			gap: 0.45rem;
		}

		.drawing-answer-card > p {
			font-size: 0.85rem;
			line-height: 1.2;
		}

		.drawing-input-fill {
			min-height: 0;
		}
	}
</style>
