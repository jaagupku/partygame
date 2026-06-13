<script lang="ts">
	import 'iconify-icon';
	import type { InputKindPresentation } from './helpers';

	type Props = {
		selectedKind: PlayerInputKind;
		inputKindDetails: Record<PlayerInputKind, InputKindPresentation>;
		onSelect: (kind: PlayerInputKind) => void;
	};

	let { selectedKind, inputKindDetails, onSelect }: Props = $props();
</script>

<div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
	{#each Object.values(inputKindDetails) as details}
		<button
			type="button"
			class={`rounded-[1.5rem] border p-4 text-left transition ${
				selectedKind === details.kind
					? 'editor-choice-card-active shadow-sm'
					: 'editor-choice-card-muted hover:border-sky-200'
			}`}
			onclick={() => onSelect(details.kind)}
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
