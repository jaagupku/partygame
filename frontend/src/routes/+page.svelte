<script lang="ts">
	import { goto } from '$app/navigation';

	import PageTopChips from '$lib/components/PageTopChips.svelte';
	import { messages } from '$lib/i18n';
</script>

<PageTopChips />

<div class="md:pt-8">
	<h1 class="page-title">{$messages.home.title}</h1>
	<p class="page-subtitle">{$messages.home.subtitle}</p>

	<div class="stack-lg">
		<button class="btn btn-primary min-h-24 text-3xl md:text-4xl" onclick={() => goto('/create')}>
			{$messages.home.create}
		</button>
		<button class="btn btn-accent min-h-24 text-3xl md:text-4xl" onclick={() => goto('/play')}>
			{$messages.home.join}
		</button>
	</div>
</div>
