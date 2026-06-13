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
	class="theme-surface-raised sticky top-0 z-20 mb-4 overflow-x-auto rounded-[1.75rem] border p-2 backdrop-blur"
>
	<div class="flex min-w-max gap-2">
		{#each sections as section}
			<button
				type="button"
				class="theme-surface-muted inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-bold transition hover:border-sky-300"
				onclick={() => scrollToSection(section.id)}
			>
				<iconify-icon icon={section.icon}></iconify-icon>
				{section.label}
			</button>
		{/each}
	</div>
</div>
