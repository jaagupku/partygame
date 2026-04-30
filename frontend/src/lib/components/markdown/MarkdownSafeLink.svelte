<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = {
		href?: string;
		title?: string;
		children?: Snippet;
	};

	let { href = '', title = undefined, children }: Props = $props();

	const safeHref = $derived(/^(https?:|mailto:|tel:)/i.test(href) ? href : '');
</script>

{#if safeHref}
	<a href={safeHref} {title} target="_blank" rel="noreferrer noopener">{@render children?.()}</a>
{:else}
	<span>{@render children?.()}</span>
{/if}
