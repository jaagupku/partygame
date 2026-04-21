<script lang="ts">
	import 'iconify-icon';
	import { getYouTubeMedia } from '$lib/media/youtube.js';
	import {
		DEFAULT_ZOOM_OUT_ORIGIN_X,
		DEFAULT_ZOOM_OUT_ORIGIN_Y,
		DEFAULT_ZOOM_OUT_START
	} from '$lib/media/image-reveal';
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

	function getImageMedia(media: StepDefinition['media']): ImageMediaDefinition | null {
		return media?.type_ === 'image' ? media : null;
	}

	function getMediaTypeLabel(mediaType: string) {
		if (mediaType === 'image') {
			return 'Image';
		}
		if (mediaType === 'audio') {
			return 'Audio';
		}
		return 'Video';
	}

	function getMediaTypeHelp(mediaType: string) {
		if (mediaType === 'image') {
			return $messages.editor.mediaTypeImageHelp;
		}
		if (mediaType === 'audio') {
			return $messages.editor.mediaTypeAudioHelp;
		}
		return $messages.editor.mediaTypeVideoHelp;
	}

	function getMediaTypeAccept(mediaType: string) {
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

	function getImagePreviewStyle() {
		const imageMedia = getImageMedia(step.media);
		if (!imageMedia) {
			return '';
		}
		if (imageMedia.reveal !== 'zoom_out') {
			return '';
		}
		const zoom = imageMedia.zoom_start ?? DEFAULT_ZOOM_OUT_START;
		const originX = (imageMedia.zoom_origin_x ?? DEFAULT_ZOOM_OUT_ORIGIN_X) * 100;
		const originY = (imageMedia.zoom_origin_y ?? DEFAULT_ZOOM_OUT_ORIGIN_Y) * 100;
		return `transform: scale(${zoom}); transform-origin: ${originX}% ${originY}%;`;
	}

	const ZOOM_SLIDER_MIN = 0;
	const ZOOM_SLIDER_MAX = 9;
	const ZOOM_SLIDER_STEP = 0.1;

	function zoomFactorFromSlider(value: number) {
		return 2 ** (value / 2);
	}

	function zoomSliderFromFactor(value: number) {
		return Math.max(ZOOM_SLIDER_MIN, Math.min(ZOOM_SLIDER_MAX, Math.log2(value) * 2));
	}

	function getZoomSliderValue() {
		const imageMedia = getImageMedia(step.media);
		return zoomSliderFromFactor(imageMedia?.zoom_start ?? DEFAULT_ZOOM_OUT_START);
	}

	function getZoomDisplayValue() {
		return zoomFactorFromSlider(getZoomSliderValue());
	}

	function bindOptionalNumber(
		event: Event,
		assign: (value: number | undefined) => void,
		{
			min,
			max
		}: {
			min?: number;
			max?: number;
		} = {}
	) {
		const input = event.currentTarget as HTMLInputElement;
		const raw = input.value.trim();
		if (!raw) {
			assign(undefined);
			return;
		}
		const parsed = Number(raw);
		if (Number.isNaN(parsed)) {
			return;
		}
		const bounded = Math.min(max ?? parsed, Math.max(min ?? parsed, parsed));
		assign(bounded);
	}

	function setZoomFocusFromPreview(event: MouseEvent) {
		const imageMedia = getImageMedia(step.media);
		if (!imageMedia || imageMedia.reveal !== 'zoom_out') {
			return;
		}
		const target = event.currentTarget as HTMLElement;
		const rect = target.getBoundingClientRect();
		if (rect.width <= 0 || rect.height <= 0) {
			return;
		}
		const x = Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1);
		const y = Math.min(Math.max((event.clientY - rect.top) / rect.height, 0), 1);
		imageMedia.zoom_origin_x = x;
		imageMedia.zoom_origin_y = y;
	}

	function resetZoomDefaults() {
		const imageMedia = getImageMedia(step.media);
		if (!imageMedia) {
			return;
		}
		imageMedia.zoom_start = undefined;
		imageMedia.zoom_origin_x = undefined;
		imageMedia.zoom_origin_y = undefined;
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

						{#if step.media.reveal === 'zoom_out'}
							<div class="grid gap-4 md:grid-cols-3">
								<label class="input-wrap">
									<div class="flex items-center justify-between gap-3">
										<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
											{$messages.editor.zoomStart}
										</span>
										<span class="text-sm font-semibold text-slate-700">
											{getZoomDisplayValue().toFixed(1)}x
										</span>
									</div>
									<input
										type="range"
										min={ZOOM_SLIDER_MIN}
										max={ZOOM_SLIDER_MAX}
										step={ZOOM_SLIDER_STEP}
										class="h-3 w-full cursor-pointer accent-sky-500"
										value={getZoomSliderValue()}
										oninput={(event) =>
											bindOptionalNumber(event, (value) => {
												const imageMedia = getImageMedia(step.media);
												if (!imageMedia) {
													return;
												}
												imageMedia.zoom_start =
													value === undefined ? undefined : zoomFactorFromSlider(value);
											}, { min: ZOOM_SLIDER_MIN, max: ZOOM_SLIDER_MAX })}
									/>
									<p class="text-sm text-slate-500">{$messages.editor.zoomStartHelp}</p>
								</label>

								<label class="input-wrap">
									<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
										{$messages.editor.zoomOriginX}
									</span>
									<input
										type="number"
										min="0"
										max="100"
										step="1"
										class="input text-lg"
										value={step.media.zoom_origin_x !== undefined
											? step.media.zoom_origin_x * 100
											: ''}
										placeholder="58"
										oninput={(event) =>
											bindOptionalNumber(event, (value) => {
												const imageMedia = getImageMedia(step.media);
												if (!imageMedia) {
													return;
												}
												imageMedia.zoom_origin_x =
													value === undefined ? undefined : value / 100;
											}, { min: 0, max: 100 })}
									/>
									<p class="text-sm text-slate-500">{$messages.editor.zoomOriginXHelp}</p>
								</label>

								<label class="input-wrap">
									<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
										{$messages.editor.zoomOriginY}
									</span>
									<input
										type="number"
										min="0"
										max="100"
										step="1"
										class="input text-lg"
										value={step.media.zoom_origin_y !== undefined
											? step.media.zoom_origin_y * 100
											: ''}
										placeholder="42"
										oninput={(event) =>
											bindOptionalNumber(event, (value) => {
												const imageMedia = getImageMedia(step.media);
												if (!imageMedia) {
													return;
												}
												imageMedia.zoom_origin_y =
													value === undefined ? undefined : value / 100;
											}, { min: 0, max: 100 })}
									/>
									<p class="text-sm text-slate-500">{$messages.editor.zoomOriginYHelp}</p>
								</label>
							</div>
							<div class="flex flex-wrap items-center gap-3 text-sm text-slate-500">
								<p>{$messages.editor.zoomFocusPreviewHelp}</p>
								<button class="btn btn-ghost text-sm" type="button" onclick={resetZoomDefaults}>
									{$messages.editor.resetZoomDefaults}
								</button>
							</div>
						{/if}
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
							<div class="mt-3 grid gap-2">
								<button
									type="button"
									class={`relative overflow-hidden rounded-2xl bg-slate-100 ${
										step.media.reveal === 'zoom_out'
											? 'cursor-crosshair'
											: 'cursor-default'
									}`}
									onclick={setZoomFocusFromPreview}
								>
									<img
										src={step.media.src}
										alt={step.title}
										class="max-h-64 w-full object-cover transition-transform duration-200"
										style={getImagePreviewStyle()}
									/>
									{#if step.media.reveal === 'zoom_out'}
										<div
											class="pointer-events-none absolute h-7 w-7 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-sky-500/30 shadow-[0_0_0_1px_rgba(14,165,233,0.6)]"
											style={`left:${(step.media.zoom_origin_x ?? DEFAULT_ZOOM_OUT_ORIGIN_X) * 100}%; top:${(step.media.zoom_origin_y ?? DEFAULT_ZOOM_OUT_ORIGIN_Y) * 100}%;`}
										></div>
									{/if}
								</button>
								{#if step.media.reveal === 'zoom_out'}
									<p class="text-xs text-slate-500">{$messages.editor.zoomFocusPreviewCaption}</p>
								{/if}
							</div>
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
