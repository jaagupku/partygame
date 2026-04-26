<script lang="ts">
	import { messages } from '$lib/i18n';
	import EditorSectionCard from './EditorSectionCard.svelte';
	import MarkdownBodyEditor from './MarkdownBodyEditor.svelte';
	import MediaEditor from './MediaEditor.svelte';

	type Props = {
		step: StepDefinition;
		showAdvancedFields: boolean;
		uploadKey: string | null;
		onAddMedia: (step: StepDefinition) => void;
		onRemoveMedia: (step: StepDefinition) => void;
		onUpdateMediaType: (step: StepDefinition, mediaType: 'image' | 'audio' | 'video') => void;
		onUploadMedia: (event: Event, step: StepDefinition, stepId: string) => void;
	};

	let {
		step,
		showAdvancedFields,
		uploadKey,
		onAddMedia,
		onRemoveMedia,
		onUpdateMediaType,
		onUploadMedia
	}: Props = $props();
</script>

<EditorSectionCard
	id="main-screen"
	icon="fluent:desktop-16-filled"
	iconClass="bg-sky-100 text-sky-700"
	title={$messages.editor.mainScreen}
	description={$messages.editor.mainScreenHelp}
>
	<div class="grid gap-4">
		<label class="input-wrap">
			<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
				{$messages.editor.stepTitle}
			</span>
			<input
				bind:value={step.title}
				class="input text-lg"
				placeholder={$messages.editor.stepTitlePlaceholder}
			/>
		</label>
		<MarkdownBodyEditor {step} />
		{#if showAdvancedFields}
			<label class="input-wrap">
				<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
					{$messages.editor.stepId}
				</span>
				<input bind:value={step.id} class="input text-lg" />
			</label>
		{/if}
	</div>

	<div class="mt-6">
		<MediaEditor
			{step}
			{uploadKey}
			{onAddMedia}
			{onRemoveMedia}
			{onUpdateMediaType}
			{onUploadMedia}
		/>
	</div>
</EditorSectionCard>
