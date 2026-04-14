<script lang="ts">
	import 'iconify-icon';
	import StepDisplayPreview from '$lib/components/StepDisplayPreview.svelte';
	import { messages } from '$lib/i18n';

	type Props = {
		step?: RuntimeStepState;
		countdown: number;
		onClose: () => void;
	};

	let { step, countdown, onClose }: Props = $props();

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			onClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="fixed inset-0 z-50 overflow-y-auto bg-slate-950/55 p-4 md:p-8">
	<div
		class="mx-auto w-full max-w-[90rem] rounded-[2rem] border border-slate-200 bg-white p-6 shadow-2xl md:p-8"
	>
		<div class="mb-6 flex flex-wrap items-start justify-between gap-4">
			<div>
				<h3 class="label-title text-2xl">{$messages.editor.displayPreview}</h3>
				<p class="text-sm text-slate-600">{$messages.editor.displayPreviewHelp}</p>
			</div>
			<button
				type="button"
				class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-600"
				aria-label={$messages.editor.closeDisplayPreview}
				onclick={onClose}
			>
				<iconify-icon icon="fluent:dismiss-16-filled"></iconify-icon>
			</button>
		</div>

		<div
			class="rounded-4xl bg-[radial-gradient(circle_at_10%_15%,#c7f1ff_0,transparent_30%),radial-gradient(circle_at_85%_10%,#fff0c9_0,transparent_32%),radial-gradient(circle_at_78%_84%,#d7ffda_0,transparent_30%),linear-gradient(135deg,#f8fff1,#ddf2ff_42%,#fff4db)] p-4 md:p-8"
		>
			<StepDisplayPreview
				{step}
				phaseLabel="question_active"
				connectionLabel={$messages.common.preview}
				{countdown}
			/>
		</div>
	</div>
</div>
