<script lang="ts">
	export let href = '';
	export let title: string | undefined = undefined;

	$: safeHref = /^(https?:|mailto:|tel:)/i.test(href) ? href : '';
</script>

{#if safeHref}
	<a href={safeHref} {title} target="_blank" rel="noreferrer noopener"><slot /></a>
{:else}
	<span><slot /></span>
{/if}
