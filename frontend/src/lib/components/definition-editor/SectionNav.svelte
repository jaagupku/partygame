<script lang="ts">
	import 'iconify-icon';

	type SectionItem = {
		id: string;
		label: string;
		icon: string;
	};

	type Props = {
		sections: SectionItem[];
	};

	let { sections }: Props = $props();

	function scrollToSection(sectionId: string) {
		document.getElementById(sectionId)?.scrollIntoView({
			behavior: 'smooth',
			block: 'start'
		});
	}
</script>

<div
	class="sticky top-0 z-20 mb-4 overflow-x-auto rounded-[1.75rem] border border-slate-200 bg-white/92 p-2 shadow-sm backdrop-blur"
>
	<div class="flex min-w-max gap-2">
		{#each sections as section}
			<button
				type="button"
				class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-bold text-slate-700 transition hover:border-sky-300 hover:bg-sky-50"
				onclick={() => scrollToSection(section.id)}
			>
				<iconify-icon icon={section.icon}></iconify-icon>
				{section.label}
			</button>
		{/each}
	</div>
</div>
