<script lang="ts">
	import 'iconify-icon';

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

<div class="fixed inset-0 z-50 overflow-y-auto bg-slate-950/55 p-4 md:p-8">
	<div
		class="mx-auto w-full max-w-2xl rounded-[2rem] border border-slate-200 bg-white p-6 shadow-2xl"
	>
		<div class="mb-6 flex flex-wrap items-start justify-between gap-4">
			<div>
				<h3 class="label-title text-2xl">Editor Shortcuts</h3>
				<p class="text-sm text-slate-600">
					These shortcuts work while the definition editor is active.
				</p>
			</div>
			<button
				type="button"
				class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-600"
				aria-label="Close shortcut help"
				onclick={onClose}
			>
				<iconify-icon icon="fluent:dismiss-16-filled"></iconify-icon>
			</button>
		</div>

		<div class="grid gap-4 md:grid-cols-3">
			{#each groups as group}
				<section class="rounded-2xl bg-slate-50 p-4">
					<h4 class="text-sm font-bold uppercase tracking-wide text-slate-500">{group.title}</h4>
					<div class="mt-3 space-y-3">
						{#each group.items as item}
							<div class="flex items-center justify-between gap-3">
								<span class="text-sm font-medium text-slate-700">{item.label}</span>
								<kbd
									class="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-slate-600"
								>
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
