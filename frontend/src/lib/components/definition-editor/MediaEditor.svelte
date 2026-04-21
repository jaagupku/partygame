<script lang="ts">
	import 'iconify-icon';
	import { getYouTubeMedia } from '$lib/media/youtube.js';
	import { messages } from '$lib/i18n';
	import { IMAGE_REVEALS, MEDIA_TYPES } from './helpers';

	type Props = {
		step: StepDefinition;
		uploadKey: string | null;
		onAddMedia: (step: StepDefinition) => void;
		onRemoveMedia: (step: StepDefinition) => void;
		onUpdateMediaType: (step: StepDefinition, mediaType: (typeof MEDIA_TYPES)[number]) => void;
		onUploadMedia: (event: Event, step: StepDefinition, stepId: string) => void;
	};

	let { step, uploadKey, onAddMedia, onRemoveMedia, onUpdateMediaType, onUploadMedia }: Props =
		$props();

	function getMediaTypeLabel(mediaType: (typeof MEDIA_TYPES)[number]) {
		if (mediaType === 'image') {
			return 'Image';
		}
		if (mediaType === 'audio') {
			return 'Audio';
		}
		return 'Video';
	}

	function getMediaTypeHelp(mediaType: (typeof MEDIA_TYPES)[number]) {
		if (mediaType === 'image') {
			return $messages.editor.mediaTypeImageHelp;
		}
		if (mediaType === 'audio') {
			return $messages.editor.mediaTypeAudioHelp;
		}
		return $messages.editor.mediaTypeVideoHelp;
	}

	function getMediaTypeAccept(mediaType: (typeof MEDIA_TYPES)[number]) {
		if (mediaType === 'image') {
			return 'image/*,.png,.jpg,.jpeg,.gif,.webp,.svg,.avif';
		}
		if (mediaType === 'audio') {
			return 'audio/*,.mp3,.wav,.ogg,.m4a,.aac,.flac';
		}
		return 'video/*,.mp4,.webm,.mov,.m4v,.ogv';
	}

	function getPreviewYouTubeEmbed(): string | null {
		if (step.media?.type_ !== 'video') {
			return null;
		}
		return (
			getYouTubeMedia(step.media.src, {
				controls: false,
				loop: step.media.loop,
				origin: typeof window !== 'undefined' ? window.location.origin : undefined
			})?.embedUrl ?? null
		);
	}

	function getRevealLabel(revealMode: (typeof IMAGE_REVEALS)[number]) {
		return $messages.editor.imageReveal[revealMode].label;
	}
</script>

<div class="rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div>
			<p class="text-lg font-bold text-slate-900">{$messages.editor.questionMedia}</p>
			<p class="text-sm text-slate-600">{$messages.editor.questionMediaHelp}</p>
		</div>
		{#if step.media}
			<button class="btn btn-danger text-sm" type="button" onclick={() => onRemoveMedia(step)}>
				{$messages.editor.removeMedia}
			</button>
		{:else}
			<button class="btn btn-ghost text-sm" type="button" onclick={() => onAddMedia(step)}>
				{$messages.editor.addMedia}
			</button>
		{/if}
	</div>

	{#if step.media}
		<div class="mt-4 grid gap-4">
			<div class="grid gap-3 md:grid-cols-3">
				{#each MEDIA_TYPES as mediaType}
					<button
						type="button"
						class={`rounded-[1.35rem] border px-4 py-4 text-left transition ${
							step.media.type_ === mediaType
								? 'border-sky-300 bg-sky-50 shadow-sm'
								: 'border-slate-200 bg-white hover:border-sky-200 hover:bg-sky-50/50'
						}`}
						onclick={() => onUpdateMediaType(step, mediaType)}
					>
						<p class="text-base font-bold text-slate-900">{getMediaTypeLabel(mediaType)}</p>
						<p class="mt-1 text-sm text-slate-600">{getMediaTypeHelp(mediaType)}</p>
					</button>
				{/each}
			</div>

			<div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
				<div class="grid gap-4">
					<label class="input-wrap">
						<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
							{$messages.editor.sourceUrl}
						</span>
						<input
							bind:value={step.media.src}
							class="input text-lg"
							placeholder={step.media.type_ === 'video'
								? $messages.editor.videoSourceUrlPlaceholder
								: $messages.editor.sourceUrlPlaceholder}
						/>
						{#if step.media.type_ === 'video'}
							<p class="text-sm text-slate-500">{$messages.editor.videoSourceHelp}</p>
						{/if}
					</label>

					{#if step.media.type_ === 'image'}
						<div class="grid gap-3 md:grid-cols-2">
							{#each IMAGE_REVEALS as revealMode}
								<button
									type="button"
									class={`rounded-[1.25rem] border px-4 py-3 text-left transition ${
										step.media.reveal === revealMode
											? 'border-sky-300 bg-sky-50'
											: 'border-slate-200 bg-white hover:border-sky-200'
									}`}
									onclick={() => (step.media ? (step.media.reveal = revealMode) : null)}
								>
									<p class="text-sm font-bold uppercase tracking-wide text-slate-700">
										{getRevealLabel(revealMode)}
									</p>
									<p class="mt-1 text-sm text-slate-600">
										{$messages.editor.imageReveal[revealMode].description}
									</p>
								</button>
							{/each}
						</div>
					{/if}

					<label class="flex items-center justify-between gap-4 rounded-2xl bg-white px-4 py-3">
						<div>
							<p class="text-lg font-bold">{$messages.editor.loopMedia}</p>
							<p class="text-sm text-slate-600">{$messages.editor.loopMediaHelp}</p>
						</div>
						<input bind:checked={step.media.loop} type="checkbox" class="h-5 w-5" />
					</label>

					<label class="input-wrap">
						<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
							{$messages.editor.uploadFile}
						</span>
						<input
							type="file"
							accept={getMediaTypeAccept(step.media.type_)}
							class="input text-base file:mr-4 file:rounded-xl file:border-0 file:bg-sky-100 file:px-3 file:py-2 file:font-semibold file:text-sky-700"
							onchange={(event) => onUploadMedia(event, step, step.id)}
						/>
					</label>

					{#if uploadKey === step.id}
						<p class="text-sm font-semibold text-sky-700">{$messages.editor.uploadingMedia}</p>
					{/if}
				</div>

				<div class="rounded-[1.5rem] border border-slate-200 bg-white p-4">
					<p class="text-sm font-bold uppercase tracking-[0.18em] text-slate-500">
						{$messages.common.preview}
					</p>
					{#if step.media.src}
						{#if step.media.type_ === 'image'}
							<img
								src={step.media.src}
								alt={step.title}
								class="mt-3 max-h-64 w-full rounded-2xl object-cover"
							/>
						{:else if step.media.type_ === 'audio'}
							<audio class="mt-3 w-full" controls src={step.media.src}></audio>
						{:else if step.media.type_ === 'video'}
							{@const youtubeEmbedUrl = getPreviewYouTubeEmbed()}
							{#if youtubeEmbedUrl}
								<iframe
									class="mt-3 aspect-video w-full rounded-2xl border-0"
									src={youtubeEmbedUrl}
									title={`${step.title || $messages.common.question} video preview`}
									allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
									referrerpolicy="strict-origin-when-cross-origin"
									allowfullscreen
								></iframe>
							{:else}
								<video
									class="mt-3 max-h-64 w-full rounded-2xl"
									controls
									loop={step.media.loop}
									src={step.media.src}
								>
									<track kind="captions" />
								</video>
							{/if}
						{/if}
						<p class="mt-3 text-xs text-slate-500">{step.media.src}</p>
					{:else}
						<p class="mt-3 text-sm text-slate-500">{$messages.editor.previewHelp}</p>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
