<script lang="ts">
	import { messages } from '$lib/i18n';
	import { triggerBuzzerHapticPulse } from '$lib/haptics.js';
	import OrderingList from '$lib/components/OrderingList.svelte';

	interface PlayerInputPanelProps {
		activeStep?: RuntimeStepState;
		baseInputDisabled: boolean;
		buzzerActive: boolean;
		canContinueHostlessInfoSlide: boolean;
		disabledBuzzerPlayerIds: string[];
		hasSubmitted: boolean;
		playerId: string;
		onContinueInfoSlide: () => void;
		onSubmitAnswer: (value: unknown) => void;
	}

	let {
		activeStep,
		baseInputDisabled,
		buzzerActive,
		canContinueHostlessInfoSlide,
		disabledBuzzerPlayerIds,
		hasSubmitted,
		playerId,
		onContinueInfoSlide,
		onSubmitAnswer
	}: PlayerInputPanelProps = $props();

	let answerValue = $state<string | number>('');
	let orderingItems = $state<string[]>([]);
	let selectedRadioOption = $state<string | null>(null);
	let selectedCheckboxOptions = $state<string[]>([]);
	let orderingStepId = $state<string | undefined>(undefined);
	let inputStepId = $state<string | undefined>(undefined);
	let pendingSubmissionStepId = $state<string | undefined>(undefined);

	const inputDisabled = $derived(baseInputDisabled || pendingSubmissionStepId === activeStep?.id);
	const buzzerLockedOut = $derived(disabledBuzzerPlayerIds.includes(playerId));

	$effect(() => {
		const step = activeStep;
		if (step?.id !== inputStepId) {
			answerValue = '';
			selectedRadioOption = null;
			selectedCheckboxOptions = [];
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

	function submitAnswer() {
		const step = activeStep;
		if (!step || inputDisabled) {
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
		} else if (step.input_kind === 'text') {
			value = String(answerValue);
		}

		pendingSubmissionStepId = step.id;
		onSubmitAnswer(value);
	}

	function buzz() {
		if (inputDisabled || buzzerLockedOut || !buzzerActive) {
			return;
		}
		triggerBuzzerHapticPulse();
		pendingSubmissionStepId = activeStep?.id;
		onSubmitAnswer('buzz');
	}

	function submitRadioOption(option: string) {
		selectedRadioOption = option;
		answerValue = option;
		submitAnswer();
	}

	function toggleCheckboxOption(option: string) {
		if (selectedCheckboxOptions.includes(option)) {
			selectedCheckboxOptions = selectedCheckboxOptions.filter((entry) => entry !== option);
			return;
		}
		selectedCheckboxOptions = [...selectedCheckboxOptions, option];
	}
</script>

{#if activeStep?.input_kind === 'buzzer'}
	<section class="card stack-md text-center">
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
			disabled={inputDisabled || !buzzerActive || buzzerLockedOut}
			class="btn btn-accent text-4xl"
			onclick={buzz}
		>
			{$messages.gameplay.buzzer}
		</button>
	</section>
{:else if activeStep?.input_kind === 'text'}
	<section class="card stack-md">
		<h2 class="label-title text-2xl">{$messages.gameplay.yourAnswer}</h2>
		{#if inputDisabled}
			<p class="text-sm text-slate-600">
				{hasSubmitted
					? $messages.gameplay.answerSubmitted
					: $messages.gameplay.stepClosedAnswersDisabled}
			</p>
		{/if}
		<input
			class="input"
			type="text"
			bind:value={answerValue}
			disabled={inputDisabled}
			placeholder={activeStep?.input_placeholder ?? $messages.gameplay.typeYourAnswer}
		/>
		<button type="button" class="btn btn-primary" onclick={submitAnswer} disabled={inputDisabled}>
			{$messages.gameplay.submitAnswer}
		</button>
	</section>
{:else if activeStep?.input_kind === 'number'}
	<section class="card stack-md">
		<h2 class="label-title text-2xl">{$messages.gameplay.yourAnswer}</h2>
		{#if inputDisabled}
			<p class="text-sm text-slate-600">
				{hasSubmitted
					? $messages.gameplay.answerSubmitted
					: $messages.gameplay.stepClosedAnswersDisabled}
			</p>
		{/if}
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
		<button type="button" class="btn btn-primary" onclick={submitAnswer} disabled={inputDisabled}>
			{$messages.gameplay.submitAnswer}
		</button>
	</section>
{:else if activeStep?.input_kind === 'ordering'}
	<section class="card stack-md">
		<h2 class="label-title text-2xl">{$messages.gameplay.orderingAnswer}</h2>
		<p class="text-sm text-slate-600">
			{inputDisabled
				? hasSubmitted
					? $messages.gameplay.orderSubmitted
					: $messages.gameplay.reorderingDisabled
				: $messages.gameplay.dragOrTapItemsToOrder}
		</p>
		<OrderingList
			items={orderingItems}
			disabled={inputDisabled}
			dragLabel={$messages.gameplay.dragOrderItem}
			moveUpLabel={$messages.gameplay.moveOrderItemUp}
			moveDownLabel={$messages.gameplay.moveOrderItemDown}
			onReorder={(items) => (orderingItems = items)}
		/>
		<button type="button" class="btn btn-primary" onclick={submitAnswer} disabled={inputDisabled}>
			{$messages.gameplay.submitOrder}
		</button>
	</section>
{:else if activeStep?.input_kind === 'radio'}
	<section class="card stack-md">
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
					class="btn btn-ghost justify-start text-left text-xl"
					disabled={inputDisabled}
					onclick={() => submitRadioOption(option)}
				>
					{option}
				</button>
			{/each}
		</div>
	</section>
{:else if activeStep?.input_kind === 'checkbox'}
	<section class="card stack-md">
		<h2 class="label-title text-2xl">{$messages.gameplay.chooseOneOrMore}</h2>
		<p class="text-sm text-slate-600">
			{inputDisabled
				? hasSubmitted
					? $messages.gameplay.selectionSubmitted
					: $messages.gameplay.newSelectionsDisabled
				: $messages.gameplay.tapOptionsThenSubmit}
		</p>
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
		<button
			type="button"
			class="btn btn-primary"
			onclick={submitAnswer}
			disabled={inputDisabled || selectedCheckboxOptions.length === 0}
		>
			{$messages.gameplay.submitSelection}
		</button>
	</section>
{:else}
	<section class="card text-center">
		<p class="text-lg">{$messages.gameplay.noPhoneInput}</p>
		{#if canContinueHostlessInfoSlide}
			<p class="mt-2 text-slate-600">{$messages.gameplay.youCanContinueInfoSlide}</p>
			<button type="button" class="btn btn-primary mt-4" onclick={onContinueInfoSlide}>
				{$messages.gameplay.advanceStep}
			</button>
		{/if}
	</section>
{/if}
