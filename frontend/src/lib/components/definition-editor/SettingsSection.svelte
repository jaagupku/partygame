<script lang="ts">
	import { messages } from '$lib/i18n';
	import EditorSectionCard from './EditorSectionCard.svelte';

	type Props = {
		step: StepDefinition;
	};

	let { step }: Props = $props();
</script>

<div class="grid gap-5">
	<EditorSectionCard
		id="timer"
		icon="fluent:timer-16-filled"
		iconClass="bg-violet-100 text-violet-700"
		title={$messages.editor.timer}
		description={$messages.editor.timerHelp}
	>
		<div class="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
			<label class="input-wrap">
				<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
					{$messages.editor.timerSeconds}
				</span>
				<input bind:value={step.timer.seconds} type="number" min="0" class="input text-lg" />
			</label>
			<label
				class="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
			>
				<div>
					<p class="text-lg font-bold">{$messages.editor.enforcedTimer}</p>
					<p class="text-sm text-slate-600">{$messages.editor.enforcedTimerHelp}</p>
				</div>
				<input bind:checked={step.timer.enforced} type="checkbox" class="h-5 w-5" />
			</label>
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
				class="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
			>
				<div>
					<p class="text-sm font-semibold text-slate-900">{$messages.editor.revealAnswers}</p>
					<p class="text-xs text-slate-600">{$messages.editor.revealAnswersHelp}</p>
				</div>
				<input bind:checked={step.host_behavior.reveal_answers} type="checkbox" class="h-5 w-5" />
			</label>
			<label
				class="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
			>
				<div>
					<p class="text-sm font-semibold text-slate-900">{$messages.editor.showSubmissions}</p>
					<p class="text-xs text-slate-600">{$messages.editor.showSubmissionsHelp}</p>
				</div>
				<input bind:checked={step.host_behavior.show_submissions} type="checkbox" class="h-5 w-5" />
			</label>
			<label
				class="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
			>
				<div>
					<p class="text-sm font-semibold text-slate-900">{$messages.editor.customPoints}</p>
					<p class="text-xs text-slate-600">{$messages.editor.customPointsHelp}</p>
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
