<script lang="ts">
	import { messages } from '$lib/i18n';

	type Props = {
		media: ImageMediaDefinition;
	};

	let { media }: Props = $props();

	function setBackgroundMode(mode: 'blur' | 'solid') {
		media.blur_circle_background = mode;
		if (mode === 'solid') {
			media.blur_circle_background_color ??= '#0f172a';
		}
	}
</script>

<div class="grid gap-3 rounded-2xl bg-white p-4">
	<p class="text-sm font-bold uppercase tracking-wide text-slate-500">
		{$messages.editor.blurCircleBackground}
	</p>
	<div class="grid gap-3 md:grid-cols-2">
		<button
			type="button"
			class={`rounded-[1.25rem] border px-4 py-3 text-left transition ${
				(media.blur_circle_background ?? 'blur') === 'blur'
					? 'border-sky-300 bg-sky-50'
					: 'border-slate-200 bg-white hover:border-sky-200'
			}`}
			onclick={() => setBackgroundMode('blur')}
		>
			<p class="text-sm font-bold text-slate-800">
				{$messages.editor.blurCircleBackgroundBlur}
			</p>
		</button>
		<button
			type="button"
			class={`rounded-[1.25rem] border px-4 py-3 text-left transition ${
				media.blur_circle_background === 'solid'
					? 'border-sky-300 bg-sky-50'
					: 'border-slate-200 bg-white hover:border-sky-200'
			}`}
			onclick={() => setBackgroundMode('solid')}
		>
			<p class="text-sm font-bold text-slate-800">
				{$messages.editor.blurCircleBackgroundSolid}
			</p>
		</button>
	</div>
	{#if media.blur_circle_background === 'solid'}
		<label class="grid gap-2">
			<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
				{$messages.editor.blurCircleBackgroundColor}
			</span>
			<input
				type="color"
				value={media.blur_circle_background_color ?? '#0f172a'}
				class="h-12 w-24 cursor-pointer rounded-xl border border-slate-200 bg-white p-1"
				oninput={(event) => {
					media.blur_circle_background_color = (event.currentTarget as HTMLInputElement).value;
				}}
			/>
		</label>
	{/if}
</div>
