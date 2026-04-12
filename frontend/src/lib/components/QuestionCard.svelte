<script lang="ts">
	interface QuestionCardProps {
		step?: RuntimeStepState;
		title?: string;
		revealedSubmission?: RevealedSubmission;
		variant?: 'default' | 'stage';
	}

	let {
		step,
		title = 'Question',
		revealedSubmission,
		variant = 'default'
	}: QuestionCardProps = $props();
	const imageRevealClass = $derived(
		step?.media?.reveal ? `reveal-${step.media.reveal}` : 'reveal-none'
	);
	const stageVariant = $derived(variant === 'stage');
</script>

<section class={`question-card card stack-md ${stageVariant ? 'question-card-stage' : ''}`}>
	<h2 class={`label-title ${stageVariant ? 'text-4xl md:text-5xl' : 'text-3xl'}`}>{title}</h2>
	{#if step}
		<h3 class={stageVariant ? 'text-4xl font-extrabold md:text-6xl' : 'text-3xl font-extrabold'}>
			{step.title}
		</h3>
		{#if step.body}
			<p class={stageVariant ? 'max-w-[60rem] text-2xl leading-relaxed md:text-3xl' : 'text-xl'}>
				{step.body}
			</p>
		{/if}
		{#if step.media?.type_ === 'image'}
			<div class={`media-frame ${imageRevealClass}`}>
				<img src={step.media.src} alt={step.title} class="media-image" />
				{#if step.media.reveal === 'blur_circle'}
					<div class="media-spotlight" style={`background-image:url('${step.media.src}')`}></div>
				{/if}
			</div>
		{:else if step.media?.type_ === 'audio'}
			<audio class="w-full" controls src={step.media.src}></audio>
		{:else if step.media?.type_ === 'video'}
			<video
				class={`w-full rounded-xl ${stageVariant ? 'max-h-[65vh] object-cover' : ''}`}
				controls
				loop={step.media.loop}
				src={step.media.src}
			>
				<track kind="captions" />
			</video>
		{/if}
		{#if revealedSubmission}
			<div
				class={`rounded-2xl bg-sky-50 px-4 py-3 ${stageVariant ? 'text-xl md:text-2xl' : 'text-lg'}`}
			>
				<span class="font-bold">Revealed answer:</span>
				{String(revealedSubmission.value)}
			</div>
		{/if}
	{:else}
		<p class="text-lg text-slate-500">Waiting for next question...</p>
	{/if}
</section>

<style lang="postcss">
	.media-frame {
		position: relative;
		overflow: hidden;
		border-radius: 1rem;
		background: rgba(15, 23, 42, 0.08);
	}

	.question-card-stage {
		padding: 1.75rem;
	}

	.media-image {
		display: block;
		width: 100%;
		height: auto;
		object-fit: cover;
	}

	.question-card-stage .media-image {
		max-height: 65vh;
		object-fit: cover;
	}

	.reveal-blur_to_clear .media-image {
		animation: blur-to-clear 14s ease forwards;
		filter: blur(18px);
	}

	.reveal-zoom_out .media-image {
		animation: zoom-out 14s ease forwards;
		transform: scale(2.4);
		transform-origin: 58% 42%;
	}

	.reveal-blur_circle .media-image {
		filter: blur(18px);
	}

	.media-spotlight {
		position: absolute;
		inset: 0;
		background-position: center;
		background-size: cover;
		animation:
			spotlight-path 14s linear infinite,
			spotlight-grow 14s ease forwards;
		border-radius: 999px;
		clip-path: circle(8% at 20% 20%);
	}

	.reveal-none .media-image {
		filter: none;
		transform: none;
	}

	@keyframes blur-to-clear {
		from {
			filter: blur(18px);
			transform: scale(1.04);
		}

		to {
			filter: blur(0);
			transform: scale(1);
		}
	}

	@keyframes zoom-out {
		from {
			transform: scale(2.4);
		}

		to {
			transform: scale(1);
		}
	}

	@keyframes spotlight-path {
		0% {
			clip-path: circle(10% at 18% 25%);
		}

		25% {
			clip-path: circle(13% at 78% 22%);
		}

		50% {
			clip-path: circle(16% at 70% 72%);
		}

		75% {
			clip-path: circle(20% at 24% 78%);
		}

		100% {
			clip-path: circle(24% at 52% 46%);
		}
	}

	@keyframes spotlight-grow {
		from {
			opacity: 0.95;
		}

		to {
			opacity: 1;
		}
	}
</style>
