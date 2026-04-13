<script lang="ts">
	import 'iconify-icon';

	type Props = {
		id?: string;
		icon: string;
		iconClass: string;
		title: string;
		description: string;
	};

	let { id, icon, iconClass, title, description }: Props = $props();
</script>

<section {id} class="rounded-[2rem] border border-slate-200 bg-white/85 p-5 shadow-sm">
	<div class="flex items-start gap-3">
		<div
			class={`inline-flex h-12 w-12 items-center justify-center rounded-2xl text-2xl ${iconClass}`}
		>
			<iconify-icon {icon}></iconify-icon>
		</div>
		<div>
			<h3 class="label-title text-2xl">{title}</h3>
			<p class="text-sm text-slate-600">{description}</p>
		</div>
	</div>

	<div class="mt-4">
		<slot />
	</div>
</section>
