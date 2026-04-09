<script lang="ts">
	interface QuestionCardProps {
		text: string;
		image?: string;
		title?: string;
	}

	let { text, image, title = 'Question' }: QuestionCardProps = $props();
</script>

<section class="card stack-md">
	<h2 class="label-title text-3xl">{title}</h2>
	{#if text}
		<p class="text-xl font-semibold">{text}</p>
	{:else}
		<p class="text-lg text-slate-500">Waiting for next question...</p>
	{/if}
	{#if image}
		<img src={image} alt="Question media" class="w-full rounded-xl object-cover" />
	{/if}
</section>
