<script lang="ts">
	import 'iconify-icon';
	import { messages } from '$lib/i18n';

	type Props = {
		title: string;
		message: string;
		confirmLabel: string;
		onClose: () => void;
		onConfirm: () => void;
	};

	let { title, message, confirmLabel, onClose, onConfirm }: Props = $props();

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			onClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-4">
	<div class="w-full max-w-lg rounded-[2rem] border border-slate-200 bg-white p-6 shadow-2xl">
		<div class="flex items-start justify-between gap-4">
			<div>
				<h3 class="label-title text-2xl">{title}</h3>
				<p class="mt-2 text-sm text-slate-600">{message}</p>
			</div>
			<button
				type="button"
				class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-600"
				aria-label={$messages.editor.closeConfirmation}
				onclick={onClose}
			>
				<iconify-icon icon="fluent:dismiss-16-filled"></iconify-icon>
			</button>
		</div>

		<div class="mt-6 flex flex-wrap justify-end gap-3">
			<button type="button" class="btn btn-ghost" onclick={onClose}
				>{$messages.common.cancel}</button
			>
			<button type="button" class="btn btn-danger" onclick={onConfirm}>{confirmLabel}</button>
		</div>
	</div>
</div>
