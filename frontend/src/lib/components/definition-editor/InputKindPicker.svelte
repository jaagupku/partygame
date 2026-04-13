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
					? 'border-sky-300 bg-sky-50 shadow-sm'
					: 'border-slate-200 bg-white hover:border-sky-200 hover:bg-sky-50/50'
			}`}
			onclick={() => onSelect(details.kind)}
		>
			<div class="flex items-start gap-3">
				<div
					class="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-2xl text-sky-700 shadow-sm"
				>
					<iconify-icon icon={details.icon}></iconify-icon>
				</div>
				<div>
					<p class="text-base font-bold text-slate-900">{details.label}</p>
					<p class="mt-1 text-sm leading-6 text-slate-600">{details.description}</p>
				</div>
			</div>
		</button>
	{/each}
</div>
