<script lang="ts">
	import 'iconify-icon';
	import { messages } from '$lib/i18n';
	import { modalPortal } from './modalPortal';

	type Props = {
		description: string;
		definitionId: string;
		visibility: DefinitionVisibility;
		showAdvancedFields: boolean;
		isNewDefinition: boolean;
		currentDefinitionId: string;
		onDescriptionChange: (value: string) => void;
		onDefinitionIdChange: (value: string) => void;
		onVisibilityChange: (value: DefinitionVisibility) => void;
		onToggleAdvancedFields: () => void;
		onClose: () => void;
		onSave: () => void;
	};

	let {
		description,
		definitionId,
		visibility,
		showAdvancedFields,
		isNewDefinition,
		currentDefinitionId,
		onDescriptionChange,
		onDefinitionIdChange,
		onVisibilityChange,
		onToggleAdvancedFields,
		onClose,
		onSave
	}: Props = $props();

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			onClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div
	use:modalPortal
	class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-4"
>
	<div class="w-full max-w-2xl rounded-[2rem] border border-slate-200 bg-white p-6 shadow-2xl">
		<div class="flex items-start justify-between gap-4">
			<div>
				<h3 class="label-title text-2xl">{$messages.editor.detailsTitle}</h3>
				<p class="text-sm text-slate-600">{$messages.editor.detailsSubtitle}</p>
			</div>
			<button
				type="button"
				class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-600"
				aria-label={$messages.editor.closeDefinitionDetails}
				onclick={onClose}
			>
				<iconify-icon icon="fluent:dismiss-16-filled"></iconify-icon>
			</button>
		</div>

		<div class="mt-5 grid gap-4">
			<label class="input-wrap">
				<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
					>{$messages.editor.description}</span
				>
				<textarea
					value={description}
					class="input min-h-32 text-lg"
					placeholder={$messages.editor.descriptionPlaceholder}
					oninput={(event) =>
						onDescriptionChange((event.currentTarget as HTMLTextAreaElement).value)}
				></textarea>
			</label>
			<label class="input-wrap">
				<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
					>{$messages.definitions.visibility}</span
				>
				<select
					value={visibility}
					class="input select-input text-lg"
					onchange={(event) =>
						onVisibilityChange(
							(event.currentTarget as HTMLSelectElement).value as DefinitionVisibility
						)}
				>
					<option value="private">{$messages.definitions.visibilityPrivate}</option>
					<option value="login_required">{$messages.definitions.visibilityLoginRequired}</option>
					<option value="public">{$messages.definitions.visibilityPublic}</option>
				</select>
			</label>
			<div class="flex justify-start">
				<button
					type="button"
					class="btn btn-ghost px-4 py-2 text-sm"
					onclick={onToggleAdvancedFields}
				>
					{showAdvancedFields ? $messages.editor.hideAdvanced : $messages.editor.showAdvanced}
				</button>
			</div>
			{#if showAdvancedFields && isNewDefinition}
				<label class="input-wrap">
					<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
						>{$messages.editor.definitionId}</span
					>
					<input
						value={definitionId}
						class="input text-lg"
						placeholder="definition_id"
						oninput={(event) =>
							onDefinitionIdChange((event.currentTarget as HTMLInputElement).value)}
					/>
				</label>
			{:else if showAdvancedFields}
				<div class="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
					{$messages.editor.definitionIdFixed}:
					<span class="font-bold text-slate-800">{currentDefinitionId}</span>
				</div>
			{/if}
		</div>

		<div class="mt-6 flex flex-wrap justify-end gap-3">
			<button type="button" class="btn btn-ghost" onclick={onClose}
				>{$messages.common.cancel}</button
			>
			<button type="button" class="btn btn-primary" onclick={onSave}
				>{$messages.common.saveDetails}</button
			>
		</div>
	</div>
</div>
