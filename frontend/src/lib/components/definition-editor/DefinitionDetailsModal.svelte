<script lang="ts">
	import 'iconify-icon';
	import { messages } from '$lib/i18n';
	import {
		DEFINITION_THEME_MODES,
		THEME_PALETTES,
		normalizeDefinitionTheme,
		resolveThemeMode,
		type DefinitionTheme,
		type DefinitionThemeMode,
		type ThemePaletteId
	} from '$lib/theme';
	import { modalPortal } from './modalPortal';

	type Props = {
		description: string;
		definitionId: string;
		visibility: DefinitionVisibility;
		theme: DefinitionTheme;
		showAdvancedFields: boolean;
		isNewDefinition: boolean;
		currentDefinitionId: string;
		onDescriptionChange: (value: string) => void;
		onDefinitionIdChange: (value: string) => void;
		onVisibilityChange: (value: DefinitionVisibility) => void;
		onThemeChange: (theme: DefinitionTheme) => void;
		onToggleAdvancedFields: () => void;
		onClose: () => void;
		onSave: () => void;
	};

	let {
		description,
		definitionId,
		visibility,
		theme,
		showAdvancedFields,
		isNewDefinition,
		currentDefinitionId,
		onDescriptionChange,
		onDefinitionIdChange,
		onVisibilityChange,
		onThemeChange,
		onToggleAdvancedFields,
		onClose,
		onSave
	}: Props = $props();

	const paletteEntries = Object.entries(THEME_PALETTES) as [
		ThemePaletteId,
		(typeof THEME_PALETTES)[ThemePaletteId]
	][];

	const normalizedTheme = $derived(normalizeDefinitionTheme(theme));

	function updateTheme(update: Partial<DefinitionTheme>) {
		onThemeChange(normalizeDefinitionTheme({ ...normalizedTheme, ...update }));
	}

	function colorValue(value: string | null | undefined, fallback: string) {
		return value ?? fallback;
	}

	function paletteFallback(key: 'background' | 'surface' | 'ink' | 'primary' | 'accent') {
		const palette = THEME_PALETTES[normalizedTheme.palette ?? 'party'] ?? THEME_PALETTES.party;
		const mode = resolveThemeMode(normalizedTheme.mode);
		const colors = palette[mode];
		if (key === 'surface') {
			return mode === 'dark' ? '#1e293b' : '#ffffff';
		}
		return colors[key];
	}

	function resetCustomColors() {
		onThemeChange({
			mode: normalizedTheme.mode,
			palette: normalizedTheme.palette
		});
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			onClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div
	use:modalPortal
	class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 p-4"
>
	<div class="theme-surface w-full max-w-2xl rounded-[2rem] border p-6 shadow-2xl">
		<div class="flex items-start justify-between gap-4">
			<div>
				<h3 class="label-title text-2xl">{$messages.editor.detailsTitle}</h3>
				<p class="theme-text-muted text-sm">{$messages.editor.detailsSubtitle}</p>
			</div>
			<button
				type="button"
				class="theme-surface-muted inline-flex h-10 w-10 items-center justify-center rounded-full border"
				aria-label={$messages.editor.closeDefinitionDetails}
				onclick={onClose}
			>
				<iconify-icon icon="fluent:dismiss-16-filled"></iconify-icon>
			</button>
		</div>

		<div class="mt-5 grid gap-4">
			<label class="input-wrap">
				<span class="theme-text-muted text-sm font-bold uppercase tracking-wide"
					>{$messages.editor.description}</span
				>
				<textarea
					value={description}
					class="input min-h-32 text-lg"
					placeholder={$messages.editor.descriptionPlaceholder}
					oninput={(event) =>
						onDescriptionChange((event.currentTarget as HTMLTextAreaElement).value)}
				></textarea>
			</label>
			<label class="input-wrap">
				<span class="theme-text-muted text-sm font-bold uppercase tracking-wide"
					>{$messages.definitions.visibility}</span
				>
				<select
					value={visibility}
					class="input select-input text-lg"
					onchange={(event) =>
						onVisibilityChange(
							(event.currentTarget as HTMLSelectElement).value as DefinitionVisibility
						)}
				>
					<option value="private">{$messages.definitions.visibilityPrivate}</option>
					<option value="login_required">{$messages.definitions.visibilityLoginRequired}</option>
					<option value="public">{$messages.definitions.visibilityPublic}</option>
				</select>
			</label>
			<section class="theme-surface-muted rounded-2xl border p-4">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div>
						<h4 class="label-title text-xl">{$messages.theme.gameTheme}</h4>
						<p class="theme-text-muted text-sm">{$messages.theme.palette}</p>
					</div>
					<div class="theme-surface inline-flex overflow-hidden rounded-full border p-1">
						{#each DEFINITION_THEME_MODES as mode}
							<button
								type="button"
								class={`px-3 py-1.5 text-sm font-black transition ${
									normalizedTheme.mode === mode
										? 'rounded-full bg-sky-500 text-white'
										: 'theme-text-muted hover:opacity-80'
								}`}
								aria-pressed={normalizedTheme.mode === mode}
								onclick={() => updateTheme({ mode: mode as DefinitionThemeMode })}
							>
								{mode === 'light'
									? $messages.theme.light
									: mode === 'dark'
										? $messages.theme.dark
										: $messages.theme.system}
							</button>
						{/each}
					</div>
				</div>

				<div class="mt-4 grid gap-2 sm:grid-cols-2">
					{#each paletteEntries as [paletteId, palette]}
						<button
							type="button"
							class={`theme-palette-option ${
								normalizedTheme.palette === paletteId ? 'theme-palette-option-active' : ''
							}`}
							aria-pressed={normalizedTheme.palette === paletteId}
							onclick={() => updateTheme({ palette: paletteId })}
						>
							<span class="theme-palette-swatches" aria-hidden="true">
								<span style={`background:${palette.light.primary}`}></span>
								<span style={`background:${palette.light.accent}`}></span>
								<span style={`background:${palette.light.background}`}></span>
							</span>
							<span>{palette.label}</span>
						</button>
					{/each}
				</div>

				<div class="mt-4">
					<div class="mb-2 flex flex-wrap items-center justify-between gap-2">
						<p class="theme-text-muted text-sm font-black uppercase tracking-wide">
							{$messages.theme.customColors}
						</p>
						<button
							type="button"
							class="text-sm font-bold text-sky-700"
							onclick={resetCustomColors}
						>
							{$messages.theme.resetCustomColors}
						</button>
					</div>
					<div class="grid gap-3 sm:grid-cols-5">
						<label class="theme-color-input">
							<span>{$messages.theme.background}</span>
							<input
								type="color"
								value={colorValue(normalizedTheme.background, paletteFallback('background'))}
								oninput={(event) =>
									updateTheme({ background: (event.currentTarget as HTMLInputElement).value })}
							/>
						</label>
						<label class="theme-color-input">
							<span>{$messages.theme.surface}</span>
							<input
								type="color"
								value={colorValue(normalizedTheme.surface, paletteFallback('surface'))}
								oninput={(event) =>
									updateTheme({ surface: (event.currentTarget as HTMLInputElement).value })}
							/>
						</label>
						<label class="theme-color-input">
							<span>{$messages.theme.text}</span>
							<input
								type="color"
								value={colorValue(normalizedTheme.ink, paletteFallback('ink'))}
								oninput={(event) =>
									updateTheme({ ink: (event.currentTarget as HTMLInputElement).value })}
							/>
						</label>
						<label class="theme-color-input">
							<span>{$messages.theme.primary}</span>
							<input
								type="color"
								value={colorValue(normalizedTheme.primary, paletteFallback('primary'))}
								oninput={(event) =>
									updateTheme({ primary: (event.currentTarget as HTMLInputElement).value })}
							/>
						</label>
						<label class="theme-color-input">
							<span>{$messages.theme.accent}</span>
							<input
								type="color"
								value={colorValue(normalizedTheme.accent, paletteFallback('accent'))}
								oninput={(event) =>
									updateTheme({ accent: (event.currentTarget as HTMLInputElement).value })}
							/>
						</label>
					</div>
				</div>
			</section>
			<div class="flex justify-start">
				<button
					type="button"
					class="btn btn-ghost px-4 py-2 text-sm"
					onclick={onToggleAdvancedFields}
				>
					{showAdvancedFields ? $messages.editor.hideAdvanced : $messages.editor.showAdvanced}
				</button>
			</div>
			{#if showAdvancedFields && isNewDefinition}
				<label class="input-wrap">
					<span class="theme-text-muted text-sm font-bold uppercase tracking-wide"
						>{$messages.editor.definitionId}</span
					>
					<input
						value={definitionId}
						class="input text-lg"
						placeholder="definition_id"
						oninput={(event) =>
							onDefinitionIdChange((event.currentTarget as HTMLInputElement).value)}
					/>
				</label>
			{:else if showAdvancedFields}
				<div class="theme-surface-muted rounded-2xl px-4 py-3 text-sm">
					{$messages.editor.definitionIdFixed}:
					<span class="theme-text font-bold">{currentDefinitionId}</span>
				</div>
			{/if}
		</div>

		<div class="mt-6 flex flex-wrap justify-end gap-3">
			<button type="button" class="btn btn-ghost" onclick={onClose}
				>{$messages.common.cancel}</button
			>
			<button type="button" class="btn btn-primary" onclick={onSave}
				>{$messages.common.saveDetails}</button
			>
		</div>
	</div>
</div>

<style lang="postcss">
	.theme-palette-option {
		display: flex;
		align-items: center;
		gap: 0.7rem;
		border: 1px solid var(--party-border);
		border-radius: 1rem;
		background: var(--party-surface-strong);
		padding: 0.7rem;
		color: var(--party-ink);
		font-weight: 900;
		text-align: left;
		transition:
			border-color 150ms ease,
			box-shadow 150ms ease,
			transform 150ms ease;
	}

	.theme-palette-option:hover {
		transform: translateY(-1px);
	}

	.theme-palette-option-active {
		border-color: var(--party-soft-primary-border);
		background: var(--party-soft-primary-bg);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--party-primary), transparent 76%);
	}

	.theme-palette-swatches {
		display: inline-flex;
		overflow: hidden;
		width: 3.5rem;
		height: 1.75rem;
		flex: 0 0 auto;
		border: 1px solid var(--party-border);
		border-radius: 999px;
	}

	.theme-palette-swatches span {
		flex: 1 1 0;
	}

	.theme-color-input {
		display: grid;
		gap: 0.35rem;
		min-width: 0;
		color: var(--party-subtle);
		font-size: 0.75rem;
		font-weight: 900;
		text-transform: uppercase;
	}

	.theme-color-input input {
		width: 100%;
		min-width: 0;
		height: 2.6rem;
		border: 1px solid var(--party-border);
		border-radius: 0.8rem;
		background: var(--party-surface-strong);
		padding: 0.2rem;
	}

	.theme-palette-option:hover {
		border-color: var(--party-soft-primary-border);
		background: var(--party-soft-primary-bg);
	}
</style>
