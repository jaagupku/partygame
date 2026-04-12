<script lang="ts">
	import 'iconify-icon';
	import type { StepTemplateDefinition, StepTemplateId } from './helpers';

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

<div class="fixed inset-0 z-50 overflow-y-auto bg-slate-950/45 p-4 md:p-8">
	<div
		class="mx-auto w-full max-w-5xl rounded-[2rem] border border-slate-200 bg-white p-6 shadow-2xl md:p-8"
	>
		<div class="flex flex-wrap items-start justify-between gap-4">
			<div>
				<h3 class="label-title text-3xl">Choose A Step Type</h3>
				<p class="text-sm text-slate-600">
					Start with a question layout that matches how this slide should play.
				</p>
			</div>
			<button
				type="button"
				class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-600"
				aria-label="Close step template picker"
				onclick={onClose}
			>
				<iconify-icon icon="fluent:dismiss-16-filled"></iconify-icon>
			</button>
		</div>

		<div class="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{#each templates as template}
				<button
					type="button"
					class="group rounded-[1.75rem] border border-slate-200 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(240,249,255,0.9))] p-5 text-left shadow-sm transition hover:-translate-y-1 hover:border-sky-300 hover:shadow-lg"
					onclick={() => onSelectTemplate(template.id)}
				>
					<div class="flex items-start justify-between gap-4">
						<div
							class="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-100 text-2xl text-sky-700 transition group-hover:bg-sky-200"
						>
							<iconify-icon icon={template.icon}></iconify-icon>
						</div>
						<span
							class="rounded-full bg-white px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-slate-500"
						>
							{template.label}
						</span>
					</div>
					<p class="mt-4 text-base font-semibold text-slate-900">{template.label}</p>
					<p class="mt-2 text-sm leading-6 text-slate-600">{template.description}</p>
				</button>
			{/each}
		</div>

		<div class="mt-6 flex justify-end">
			<button type="button" class="btn btn-ghost" onclick={onClose}>Cancel</button>
		</div>
	</div>
</div>
