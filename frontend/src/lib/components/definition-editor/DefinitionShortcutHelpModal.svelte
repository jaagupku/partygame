<script lang="ts">
	import 'iconify-icon';
	import { messages } from '$lib/i18n';
	import { modalPortal } from './modalPortal';

	type ShortcutGroup = {
		title: string;
		items: Array<{
			keys: string;
			label: string;
		}>;
	};

	type Props = {
		groups: ShortcutGroup[];
		onClose: () => void;
	};

	let { groups, onClose }: Props = $props();

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			onClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div use:modalPortal class="fixed inset-0 z-50 overflow-y-auto bg-slate-950/55 p-4 md:p-8">
	<div class="theme-surface mx-auto w-full max-w-2xl rounded-[2rem] border p-6 shadow-2xl">
		<div class="mb-6 flex flex-wrap items-start justify-between gap-4">
			<div>
				<h3 class="label-title text-2xl">{$messages.editor.editorShortcuts}</h3>
				<p class="theme-text-muted text-sm">{$messages.editor.editorShortcutsHelp}</p>
			</div>
			<button
				type="button"
				class="theme-surface-muted inline-flex h-10 w-10 items-center justify-center rounded-full border"
				aria-label={$messages.editor.closeShortcutHelp}
				onclick={onClose}
			>
				<iconify-icon icon="fluent:dismiss-16-filled"></iconify-icon>
			</button>
		</div>

		<div class="grid gap-4 md:grid-cols-3">
			{#each groups as group}
				<section class="theme-surface-muted rounded-2xl p-4">
					<h4 class="theme-text-muted text-sm font-bold uppercase tracking-wide">{group.title}</h4>
					<div class="mt-3 space-y-3">
						{#each group.items as item}
							<div class="flex items-center justify-between gap-3">
								<span class="theme-text text-sm font-medium">{item.label}</span>
								<kbd class="theme-surface rounded-lg border px-2 py-1 text-xs font-semibold">
									{item.keys}
								</kbd>
							</div>
						{/each}
					</div>
				</section>
			{/each}
		</div>
	</div>
</div>
