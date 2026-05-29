<script lang="ts">
	import 'iconify-icon';
	import PlayerInputPanel from '$lib/components/controller/PlayerInputPanel.svelte';
	import StepDisplayPreview from '$lib/components/StepDisplayPreview.svelte';
	import { messages } from '$lib/i18n';

	type PreviewMode = 'display' | 'controller';

	type Props = {
		step?: RuntimeStepState;
		countdown: number;
		title?: string;
		height?: string;
		minHeight?: string;
	};

	let {
		step,
		countdown,
		title,
		height = 'min(44rem, calc(100vh - 13rem))',
		minHeight = '28rem'
	}: Props = $props();

	let previewResetKey = $state(0);
	let previewMode = $state<PreviewMode>('display');

	function resetPreviewTimer() {
		previewResetKey += 1;
	}

	function noop() {}
</script>

<div
	class="editor-preview-pane"
	style={`--editor-preview-height: ${height}; --editor-preview-min-height: ${minHeight};`}
>
	<div class="editor-preview-toolbar">
		<div class="min-w-0">
			<p class="text-sm font-bold text-slate-700">
				{title ??
					(previewMode === 'display'
						? $messages.editor.displayPreview
						: $messages.editor.controllerPreview)}
			</p>
			<div class="editor-preview-toggle" aria-label={$messages.common.preview}>
				<button
					type="button"
					class:preview-mode-active={previewMode === 'display'}
					aria-pressed={previewMode === 'display'}
					onclick={() => (previewMode = 'display')}
				>
					<iconify-icon icon="fluent:desktop-16-filled"></iconify-icon>
					{$messages.editor.displayPreviewModeDisplay}
				</button>
				<button
					type="button"
					class:preview-mode-active={previewMode === 'controller'}
					aria-pressed={previewMode === 'controller'}
					onclick={() => (previewMode = 'controller')}
				>
					<iconify-icon icon="fluent:phone-16-filled"></iconify-icon>
					{$messages.editor.displayPreviewModeController}
				</button>
			</div>
		</div>
		{#if previewMode === 'display'}
			<button
				type="button"
				class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-700 shadow-sm transition hover:border-sky-300 hover:bg-sky-50"
				onclick={resetPreviewTimer}
			>
				<iconify-icon icon="fluent:arrow-clockwise-16-filled"></iconify-icon>
				{$messages.editor.resetPreviewTimer}
			</button>
		{/if}
	</div>

	{#if previewMode === 'display'}
		<div class="editor-preview-stage">
			{#key `${step?.id ?? 'empty-step'}:${previewResetKey}`}
				<StepDisplayPreview
					{step}
					phaseLabel="question_active"
					connectionLabel={$messages.common.preview}
					{countdown}
					layoutMode="host-stage"
				/>
			{/key}
		</div>
	{:else}
		<div class="editor-preview-controller-stage">
			<div class="editor-preview-controller-frame">
				<PlayerInputPanel
					activeStep={step}
					baseInputDisabled={false}
					buzzerActive={true}
					canContinueHostlessInfoSlide={step?.input_kind === 'none'}
					disabledBuzzerPlayerIds={[]}
					drawingItems={[]}
					drawingVotedPlayerIds={[]}
					hasSubmitted={false}
					playerId="preview-player"
					mode="preview"
					onContinueInfoSlide={noop}
					onSubmitAnswer={noop}
					onSubmitDrawingVote={noop}
				/>
			</div>
		</div>
	{/if}
</div>

<style lang="postcss">
	.editor-preview-pane {
		display: grid;
		gap: 0.65rem;
		min-width: 0;
	}

	.editor-preview-toolbar {
		display: flex;
		align-items: start;
		justify-content: space-between;
		gap: 0.75rem;
		min-width: 0;
	}

	.editor-preview-toggle {
		display: inline-flex;
		margin-top: 0.4rem;
		overflow: hidden;
		border: 1px solid rgb(203 213 225);
		border-radius: 999px;
		background: rgb(241 245 249 / 0.9);
		padding: 0.15rem;
	}

	.editor-preview-toggle button {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		border-radius: 999px;
		padding: 0.45rem 0.7rem;
		color: rgb(71 85 105);
		font-size: 0.75rem;
		font-weight: 900;
		line-height: 1;
		transition:
			background 150ms ease,
			color 150ms ease,
			box-shadow 150ms ease;
	}

	.editor-preview-toggle button.preview-mode-active {
		background: white;
		color: rgb(2 132 199);
		box-shadow: 0 2px 8px rgb(15 23 42 / 0.12);
	}

	.editor-preview-stage,
	.editor-preview-controller-stage {
		height: var(--editor-preview-height);
		min-height: var(--editor-preview-min-height);
		overflow: hidden;
		border: 1px solid rgb(203 213 225 / 0.75);
		border-radius: 1.5rem;
		background:
			radial-gradient(circle at 10% 15%, #c7f1ff 0, transparent 30%),
			radial-gradient(circle at 85% 10%, #fff0c9 0, transparent 32%),
			radial-gradient(circle at 78% 84%, #d7ffda 0, transparent 30%),
			linear-gradient(135deg, #f8fff1, #ddf2ff 42%, #fff4db);
		padding: 1rem;
		box-shadow: 0 14px 34px rgb(15 23 42 / 0.12);
	}

	.editor-preview-controller-stage {
		display: grid;
		place-items: start center;
		overflow-y: auto;
		background:
			radial-gradient(circle at 15% 10%, rgb(219 234 254) 0, transparent 32%),
			linear-gradient(135deg, rgb(248 250 252), rgb(224 242 254));
	}

	.editor-preview-controller-frame {
		width: min(100%, 28rem);
		min-height: 100%;
	}

	.editor-preview-controller-frame :global(.controller-map-height) {
		height: min(31rem, calc(100vh - 22rem));
		min-height: 18rem;
	}
</style>
