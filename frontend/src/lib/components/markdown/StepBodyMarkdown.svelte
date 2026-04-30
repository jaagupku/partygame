<script lang="ts">
	import SvelteMarkdown from 'svelte-markdown';
	import MarkdownHtmlText from './MarkdownHtmlText.svelte';
	import MarkdownImageText from './MarkdownImageText.svelte';
	import MarkdownSafeLink from './MarkdownSafeLink.svelte';

	type Props = {
		source?: string;
		stageVariant?: boolean;
	};

	let { source = '', stageVariant = false }: Props = $props();

	const markdownOptions = {
		gfm: true,
		headerIds: false,
		mangle: false
	};

	const renderers: Record<string, unknown> = {
		html: MarkdownHtmlText,
		image: MarkdownImageText,
		link: MarkdownSafeLink
	};
</script>

<div
	class={`step-body-markdown ${
		stageVariant ? 'max-w-[86rem] text-[clamp(1rem,1.8vw,1.7rem)] leading-snug' : 'text-xl'
	}`}
>
	<SvelteMarkdown {source} options={markdownOptions} {renderers} />
</div>

<style lang="postcss">
	.step-body-markdown :global(:first-child) {
		margin-top: 0;
	}

	.step-body-markdown :global(:last-child) {
		margin-bottom: 0;
	}

	.step-body-markdown :global(p) {
		margin: 0.45em 0;
	}

	.step-body-markdown :global(h1),
	.step-body-markdown :global(h2),
	.step-body-markdown :global(h3),
	.step-body-markdown :global(h4),
	.step-body-markdown :global(h5),
	.step-body-markdown :global(h6) {
		margin: 0.35em 0;
		font-weight: 900;
		line-height: 1.05;
		color: rgb(15 23 42);
	}

	.step-body-markdown :global(h1) {
		font-size: 1.9em;
	}

	.step-body-markdown :global(h2) {
		font-size: 1.55em;
	}

	.step-body-markdown :global(h3) {
		font-size: 1.28em;
	}

	.step-body-markdown :global(ul),
	.step-body-markdown :global(ol) {
		margin: 0.55em 0;
		padding-left: 1.45em;
	}

	.step-body-markdown :global(ul) {
		list-style: disc;
	}

	.step-body-markdown :global(ol) {
		list-style: decimal;
	}

	.step-body-markdown :global(li + li) {
		margin-top: 0.25em;
	}

	.step-body-markdown :global(blockquote) {
		margin: 0.6em 0;
		border-left: 0.25em solid rgb(14 165 233 / 0.5);
		padding-left: 0.8em;
		color: rgb(51 65 85);
		font-style: italic;
	}

	.step-body-markdown :global(strong) {
		font-weight: 900;
	}

	.step-body-markdown :global(em) {
		font-style: italic;
	}

	.step-body-markdown :global(code) {
		border-radius: 0.35rem;
		background: rgb(226 232 240 / 0.8);
		padding: 0.08em 0.3em;
		font-size: 0.9em;
	}

	.step-body-markdown :global(a) {
		color: rgb(2 132 199);
		font-weight: 800;
		text-decoration: underline;
		text-decoration-thickness: 0.08em;
		text-underline-offset: 0.15em;
	}
</style>
