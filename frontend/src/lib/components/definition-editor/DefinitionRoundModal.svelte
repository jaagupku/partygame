<script lang="ts">
	import 'iconify-icon';

	type Props = {
		roundModalTitle: string;
		roundModalId: string;
		showRoundAdvancedFields: boolean;
		onRoundModalTitleChange: (value: string) => void;
		onRoundModalIdChange: (value: string) => void;
		onToggleAdvancedFields: () => void;
		onClose: () => void;
		onSave: () => void;
	};

	let {
		roundModalTitle,
		roundModalId,
		showRoundAdvancedFields,
		onRoundModalTitleChange,
		onRoundModalIdChange,
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

<div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-4">
	<div class="w-full max-w-xl rounded-4xl border border-slate-200 bg-white p-6 shadow-2xl">
		<div class="flex items-start justify-between gap-4">
			<div>
				<h3 class="label-title text-2xl">Edit Round</h3>
				<p class="text-sm text-slate-600">
					Update the round name used in the sorter and live game.
				</p>
			</div>
			<button
				type="button"
				class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-600"
				aria-label="Close round editor"
				onclick={onClose}
			>
				<iconify-icon icon="fluent:dismiss-16-filled"></iconify-icon>
			</button>
		</div>

		<div class="mt-5 grid gap-4">
			<label class="input-wrap">
				<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Round name</span>
				<input
					value={roundModalTitle}
					class="input text-lg"
					placeholder="Round title"
					oninput={(event) =>
						onRoundModalTitleChange((event.currentTarget as HTMLInputElement).value)}
				/>
			</label>
			<div class="flex justify-start">
				<button
					type="button"
					class="btn btn-ghost px-4 py-2 text-sm"
					onclick={onToggleAdvancedFields}
				>
					{showRoundAdvancedFields ? 'Hide Advanced' : 'Show Advanced'}
				</button>
			</div>
			{#if showRoundAdvancedFields}
				<label class="input-wrap">
					<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Round id</span>
					<input
						value={roundModalId}
						class="input text-lg"
						placeholder="round_id"
						oninput={(event) =>
							onRoundModalIdChange((event.currentTarget as HTMLInputElement).value)}
					/>
				</label>
			{/if}
		</div>

		<div class="mt-6 flex flex-wrap justify-end gap-3">
			<button type="button" class="btn btn-ghost" onclick={onClose}>Cancel</button>
			<button type="button" class="btn btn-primary" onclick={onSave}>Save Round</button>
		</div>
	</div>
</div>
