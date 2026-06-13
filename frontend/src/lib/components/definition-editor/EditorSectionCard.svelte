<script lang="ts">
	import 'iconify-icon';
	import type { Snippet } from 'svelte';

	type Props = {
		id?: string;
		icon: string;
		iconClass: string;
		title: string;
		description: string;
		children?: Snippet;
	};

	let { id, icon, iconClass, title, description, children }: Props = $props();
</script>

<section {id} class="editor-section-card rounded-[2rem] border p-5 shadow-sm">
	<div class="flex items-start gap-3">
		<div
			class={`inline-flex h-12 w-12 items-center justify-center rounded-2xl text-2xl ${iconClass}`}
		>
			<iconify-icon {icon}></iconify-icon>
		</div>
		<div>
			<h3 class="editor-text label-title text-2xl">{title}</h3>
			<p class="editor-text-muted text-sm">{description}</p>
		</div>
	</div>

	<div class="mt-4">
		{@render children?.()}
	</div>
</section>
