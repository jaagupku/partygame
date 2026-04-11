<script lang="ts">
	import 'iconify-icon';

	type Props = {
		description: string;
		definitionId: string;
		showAdvancedFields: boolean;
		isNewDefinition: boolean;
		currentDefinitionId: string;
		onDescriptionChange: (value: string) => void;
		onDefinitionIdChange: (value: string) => void;
		onToggleAdvancedFields: () => void;
		onClose: () => void;
		onSave: () => void;
	};

	let {
		description,
		definitionId,
		showAdvancedFields,
		isNewDefinition,
		currentDefinitionId,
		onDescriptionChange,
		onDefinitionIdChange,
		onToggleAdvancedFields,
		onClose,
		onSave
	}: Props = $props();
</script>

<div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-4">
	<div class="w-full max-w-2xl rounded-[2rem] border border-slate-200 bg-white p-6 shadow-2xl">
		<div class="flex items-start justify-between gap-4">
			<div>
				<h3 class="label-title text-2xl">Definition Details</h3>
				<p class="text-sm text-slate-600">
					Edit the description and other definition-wide settings.
				</p>
			</div>
			<button
				type="button"
				class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-600"
				aria-label="Close definition details"
				onclick={onClose}
			>
				<iconify-icon icon="fluent:dismiss-16-filled"></iconify-icon>
			</button>
		</div>

		<div class="mt-5 grid gap-4">
			<label class="input-wrap">
				<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Description</span>
				<textarea
					value={description}
					class="input min-h-32 text-lg"
					placeholder="What kind of experience should hosts expect?"
					oninput={(event) =>
						onDescriptionChange((event.currentTarget as HTMLTextAreaElement).value)}
				></textarea>
			</label>
			<div class="flex justify-start">
				<button
					type="button"
					class="btn btn-ghost px-4 py-2 text-sm"
					onclick={onToggleAdvancedFields}
				>
					{showAdvancedFields ? 'Hide Advanced' : 'Show Advanced'}
				</button>
			</div>
			{#if showAdvancedFields && isNewDefinition}
				<label class="input-wrap">
					<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Definition id</span
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
					Definition id is fixed after creation: <span class="font-bold text-slate-800"
						>{currentDefinitionId}</span
					>
				</div>
			{/if}
		</div>

		<div class="mt-6 flex flex-wrap justify-end gap-3">
			<button type="button" class="btn btn-ghost" onclick={onClose}>Cancel</button>
			<button type="button" class="btn btn-primary" onclick={onSave}>Save Details</button>
		</div>
	</div>
</div>
