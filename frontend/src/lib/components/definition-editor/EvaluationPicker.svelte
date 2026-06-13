<script lang="ts">
	import 'iconify-icon';
	import type { EvaluationPresentation } from './helpers';

	type Props = {
		selectedType: EvaluationType;
		availableEvaluationDetails: EvaluationPresentation[];
		onSelect: (type: EvaluationType) => void;
	};

	let { selectedType, availableEvaluationDetails, onSelect }: Props = $props();
</script>

<div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
	{#each availableEvaluationDetails as details}
		<button
			type="button"
			class={`rounded-[1.4rem] border p-4 text-left transition ${
				selectedType === details.type ? 'editor-soft-accent shadow-sm' : 'editor-choice-card-muted'
			}`}
			onclick={() => onSelect(details.type)}
		>
			<div class="flex items-start gap-3">
				<div
					class="editor-icon-tile inline-flex h-11 w-11 items-center justify-center rounded-2xl text-2xl shadow-sm"
				>
					<iconify-icon icon={details.icon}></iconify-icon>
				</div>
				<div>
					<p class="editor-text text-base font-bold">{details.label}</p>
					<p class="editor-text-muted mt-1 text-sm leading-6">{details.description}</p>
				</div>
			</div>
		</button>
	{/each}
</div>
