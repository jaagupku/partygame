<script lang="ts">
	import 'iconify-icon';
	import type { StepTemplateDefinition, StepTemplateId } from './helpers';
	import { messages } from '$lib/i18n';
	import { modalPortal } from './modalPortal';

	type Props = {
		templates: StepTemplateDefinition[];
		onClose: () => void;
		onSelectTemplate: (templateId: StepTemplateId) => void;
	};

	let { templates, onClose, onSelectTemplate }: Props = $props();

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			onClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div
	use:modalPortal
	class="editor-template-modal fixed inset-0 z-50 overflow-y-auto bg-slate-950/45 p-4 md:p-8"
>
	<div
		class="editor-template-shell theme-surface mx-auto w-full max-w-5xl rounded-[2rem] border p-6 shadow-2xl md:p-8"
	>
		<div class="flex flex-wrap items-start justify-between gap-4">
			<div>
				<h3 class="label-title text-3xl">{$messages.editor.chooseStepType}</h3>
				<p class="theme-text-muted text-sm">{$messages.editor.chooseStepTypeHelp}</p>
			</div>
			<button
				type="button"
				class="theme-surface-muted inline-flex h-10 w-10 items-center justify-center rounded-full border"
				aria-label={$messages.editor.closeStepTemplatePicker}
				onclick={onClose}
			>
				<iconify-icon icon="fluent:dismiss-16-filled"></iconify-icon>
			</button>
		</div>

		<div class="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{#each templates as template}
				<button
					type="button"
					class="editor-template-card theme-surface-muted group rounded-[1.75rem] border p-5 text-left shadow-sm transition hover:-translate-y-1 hover:border-sky-300 hover:shadow-lg"
					onclick={() => onSelectTemplate(template.id)}
				>
					<div class="flex items-start justify-between gap-4">
						<div
							class="theme-soft-primary inline-flex h-12 w-12 items-center justify-center rounded-2xl text-2xl transition"
						>
							<iconify-icon icon={template.icon}></iconify-icon>
						</div>
						<span
							class="theme-surface rounded-full px-3 py-1 text-xs font-bold uppercase tracking-[0.18em]"
						>
							{template.label}
						</span>
					</div>
					<p class="theme-text mt-4 text-base font-semibold">{template.label}</p>
					<p class="theme-text-muted mt-2 text-sm leading-6">{template.description}</p>
				</button>
			{/each}
		</div>

		<div class="mt-6 flex justify-end">
			<button type="button" class="btn btn-ghost" onclick={onClose}
				>{$messages.common.cancel}</button
			>
		</div>
	</div>
</div>

<style lang="postcss">
	.editor-template-card:hover {
		border-color: var(--party-soft-primary-border);
		background: var(--party-soft-primary-bg);
	}
</style>
