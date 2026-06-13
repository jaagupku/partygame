<script lang="ts">
	import { messages } from '$lib/i18n';
	import EditorSectionCard from './EditorSectionCard.svelte';
	import { DEFAULT_TIMER_SECONDS } from './helpers';

	type Props = {
		step: StepDefinition;
	};

	let { step }: Props = $props();

	const timerEnabled = $derived(step.timer.seconds !== undefined && step.timer.seconds !== null);

	function setTimerEnabled(event: Event) {
		const checked = (event.currentTarget as HTMLInputElement).checked;
		if (checked) {
			step.timer.seconds = DEFAULT_TIMER_SECONDS;
			return;
		}
		step.timer.seconds = undefined;
		step.timer.enforced = false;
	}
</script>

<div class="grid gap-5">
	<EditorSectionCard
		id="timer"
		icon="fluent:timer-16-filled"
		iconClass="bg-violet-100 text-violet-700"
		title={$messages.editor.timer}
		description={$messages.editor.timerHelp}
	>
		<div class="grid gap-4">
			<label
				class="editor-nested-panel flex items-center justify-between gap-4 rounded-2xl border px-4 py-3"
			>
				<div>
					<p class="editor-text text-lg font-bold">{$messages.editor.timerEnabled}</p>
					<p class="editor-text-muted text-sm">{$messages.editor.timerEnabledHelp}</p>
				</div>
				<input checked={timerEnabled} onchange={setTimerEnabled} type="checkbox" class="h-5 w-5" />
			</label>

			{#if timerEnabled}
				<div class="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
					<label class="input-wrap">
						<span class="editor-text-muted text-sm font-bold uppercase tracking-wide">
							{$messages.editor.timerSeconds}
						</span>
						<input bind:value={step.timer.seconds} type="number" min="0" class="input text-lg" />
					</label>
					<label
						class="editor-nested-panel flex items-center justify-between gap-4 rounded-2xl border px-4 py-3"
					>
						<div>
							<p class="editor-text text-lg font-bold">{$messages.editor.enforcedTimer}</p>
							<p class="editor-text-muted text-sm">{$messages.editor.enforcedTimerHelp}</p>
						</div>
						<input bind:checked={step.timer.enforced} type="checkbox" class="h-5 w-5" />
					</label>
				</div>
			{/if}
		</div>
	</EditorSectionCard>

	<EditorSectionCard
		id="host-controls"
		icon="fluent:person-settings-16-filled"
		iconClass="bg-rose-100 text-rose-700"
		title={$messages.editor.hostControls}
		description={$messages.editor.hostControlsHelp}
	>
		<div class="grid gap-3 md:grid-cols-3">
			<label
				class="editor-nested-panel flex items-center justify-between gap-3 rounded-2xl border px-4 py-3"
			>
				<div>
					<p class="editor-text text-sm font-semibold">{$messages.editor.revealAnswers}</p>
					<p class="editor-text-muted text-xs">{$messages.editor.revealAnswersHelp}</p>
				</div>
				<input bind:checked={step.host_behavior.reveal_answers} type="checkbox" class="h-5 w-5" />
			</label>
			<label
				class="editor-nested-panel flex items-center justify-between gap-3 rounded-2xl border px-4 py-3"
			>
				<div>
					<p class="editor-text text-sm font-semibold">{$messages.editor.showSubmissions}</p>
					<p class="editor-text-muted text-xs">{$messages.editor.showSubmissionsHelp}</p>
				</div>
				<input bind:checked={step.host_behavior.show_submissions} type="checkbox" class="h-5 w-5" />
			</label>
			<label
				class="editor-nested-panel flex items-center justify-between gap-3 rounded-2xl border px-4 py-3"
			>
				<div>
					<p class="editor-text text-sm font-semibold">{$messages.editor.customPoints}</p>
					<p class="editor-text-muted text-xs">{$messages.editor.customPointsHelp}</p>
				</div>
				<input
					bind:checked={step.host_behavior.allow_custom_points}
					type="checkbox"
					class="h-5 w-5"
				/>
			</label>
		</div>
	</EditorSectionCard>
</div>
