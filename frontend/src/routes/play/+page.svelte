<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import {
		AVATAR_PRESETS,
		createDefaultPlayerProfile,
		DEFAULT_AVATAR_PRESET_KEY,
		getAvatarPreset,
		normalizePlayerProfile,
		type AvatarSelectionKind
	} from '$lib/avatar-presets.js';
	import Avatar from '$lib/components/Avatar.svelte';
	import AvatarCropEditor from '$lib/components/AvatarCropEditor.svelte';
	import { createLocalStorageStore } from '$lib/local-storage-store.js';
	import { messages } from '$lib/i18n';
	import { showErrorToast, showSuccessToast } from '$lib/toast-store';
	import { onDestroy, onMount } from 'svelte';

	function randomPresetKey() {
		return (
			AVATAR_PRESETS[Math.floor(Math.random() * AVATAR_PRESETS.length)]?.key ??
			DEFAULT_AVATAR_PRESET_KEY
		);
	}

	const playerProfile = createLocalStorageStore('playerProfile', createDefaultPlayerProfile());
	const storedProfile = normalizePlayerProfile($playerProfile);
	const storedPresetKey = storedProfile.avatar_preset_key ?? DEFAULT_AVATAR_PRESET_KEY;
	const initialPresetKey =
		storedProfile.name.trim() || storedProfile.avatar_kind === 'custom'
			? storedPresetKey
			: randomPresetKey();

	const initialJoinCode =
		page.url.searchParams.get('join_code') ?? page.url.searchParams.get('code') ?? '';

	let joinCode = $state(initialJoinCode.slice(0, 5).toUpperCase());
	let name = $state(storedProfile.name);
	let avatarKind = $state<AvatarSelectionKind>(storedProfile.avatar_kind);
	let avatarPresetKey = $state<string | null>(initialPresetKey);
	let avatarUrl = $state<string | null>(storedProfile.avatar_url);
	let avatarAssetId = $state<string | null>(storedProfile.avatar_asset_id);
	let submitEnabled = $state(false);
	let uploadingAvatar = $state(false);
	let validatingProfile = $state(false);
	let pendingImageUrl = $state<string | null>(null);
	let pendingFileName = $state('avatar.png');
	let cropEditor = $state<AvatarCropEditor | null>(null);
	let avatarPickerOpen = $state(false);

	type StoredPlayerByJoinCode = Record<string, Player>;

	function uppercase(node: HTMLInputElement) {
		const transform = () => (node.value = node.value.toUpperCase());

		node.addEventListener('input', transform, { capture: true });
		transform();
	}

	function clearPendingImage() {
		if (pendingImageUrl?.startsWith('blob:')) {
			URL.revokeObjectURL(pendingImageUrl);
		}
		pendingImageUrl = null;
	}

	function setPresetAvatar(key: string) {
		avatarKind = 'preset';
		avatarPresetKey = getAvatarPreset(key)?.key ?? DEFAULT_AVATAR_PRESET_KEY;
		avatarUrl = null;
		avatarAssetId = null;
		clearPendingImage();
	}

	function getStoredPlayersByJoinCode() {
		if (!browser) {
			return {};
		}
		try {
			return JSON.parse(
				localStorage.getItem('playerDataByJoinCode') ?? '{}'
			) as StoredPlayerByJoinCode;
		} catch {
			return {};
		}
	}

	function getReconnectPlayer(joinCodeValue: string) {
		const normalizedJoinCode = joinCodeValue.toUpperCase();
		const storedPlayers = getStoredPlayersByJoinCode();
		return storedPlayers[normalizedJoinCode] ?? null;
	}

	function storeJoinedPlayer(joinCodeValue: string, player: Player) {
		if (!browser) {
			return;
		}
		const normalizedJoinCode = joinCodeValue.toUpperCase();
		const storedPlayers = getStoredPlayersByJoinCode();
		storedPlayers[normalizedJoinCode] = player;
		localStorage.setItem('playerDataByJoinCode', JSON.stringify(storedPlayers));
		localStorage.setItem('playerData', JSON.stringify(player));
	}

	async function onSubmit(event: SubmitEvent) {
		event.preventDefault();
		const trimmedName = name.trim();
		if (!submitEnabled || uploadingAvatar) {
			return;
		}
		const storedPlayer = getReconnectPlayer(joinCode);

		const res = await fetch('/api/v1/lobby/join', {
			method: 'POST',
			body: JSON.stringify({
				player_name: trimmedName,
				join_code: joinCode,
				player_id: storedPlayer?.id ?? null,
				avatar_kind: avatarKind,
				avatar_preset_key: avatarKind === 'preset' ? avatarPresetKey : null,
				avatar_url: avatarKind === 'custom' ? avatarUrl : null,
				avatar_asset_id: avatarKind === 'custom' ? avatarAssetId : null
			}),
			headers: {
				'Content-Type': 'application/json'
			}
		});
		const body: ConnectedToLobby = await res.json();
		if (!res.ok) {
			showErrorToast(
				typeof body === 'object' && body !== null && 'detail' in body
					? String(body.detail)
					: $messages.join.couldNotJoinGame
			);
			return;
		}

		$playerProfile = normalizePlayerProfile({
			name: body.player.name,
			avatar_kind: body.player.avatar_kind ?? 'preset',
			avatar_preset_key: body.player.avatar_preset_key ?? DEFAULT_AVATAR_PRESET_KEY,
			avatar_url: body.player.avatar_url ?? null,
			avatar_asset_id: body.player.avatar_asset_id ?? null
		});
		storeJoinedPlayer(body.lobby.join_code, body.player);
		goto(`/play/${body.lobby.join_code}`);
	}

	async function onAvatarFileSelected(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) {
			return;
		}
		clearPendingImage();
		pendingImageUrl = URL.createObjectURL(file);
		pendingFileName = file.name || 'avatar.png';
		input.value = '';
	}

	async function uploadCustomAvatar() {
		if (!cropEditor) {
			return;
		}
		uploadingAvatar = true;
		try {
			const blob = await cropEditor.exportBlob();
			if (!blob) {
				showErrorToast($messages.join.couldNotPrepareAvatar);
				return;
			}
			const response = await fetch(
				`/api/v1/media?kind=image&filename=${encodeURIComponent(pendingFileName.replace(/\.[^.]+$/, '') || 'avatar')}.png`,
				{
					method: 'POST',
					body: blob,
					headers: {
						'Content-Type': 'image/png'
					}
				}
			);
			const asset: MediaAsset | { detail?: string } = await response.json();
			if (!response.ok || !('id' in asset)) {
				showErrorToast(
					(typeof asset === 'object' && asset !== null && 'detail' in asset && asset.detail) ||
						$messages.join.couldNotUploadAvatar
				);
				return;
			}
			avatarKind = 'custom';
			avatarPresetKey = null;
			avatarUrl = asset.public_url;
			avatarAssetId = asset.id;
			avatarPickerOpen = false;
			clearPendingImage();
			showSuccessToast($messages.join.customAvatarReady);
		} catch {
			showErrorToast($messages.join.couldNotUploadAvatar);
		} finally {
			uploadingAvatar = false;
		}
	}

	async function validateStoredAvatar() {
		if (!browser || avatarKind !== 'custom' || !avatarAssetId) {
			return;
		}
		validatingProfile = true;
		try {
			const response = await fetch(`/api/v1/media/${avatarAssetId}/meta`);
			if (!response.ok) {
				setPresetAvatar(DEFAULT_AVATAR_PRESET_KEY);
			}
		} catch {
			setPresetAvatar(DEFAULT_AVATAR_PRESET_KEY);
		} finally {
			validatingProfile = false;
		}
	}

	$effect(() => {
		joinCode = joinCode.slice(0, 5).toUpperCase();
		name = name.slice(0, 32);
		const hasAvatar =
			(avatarKind === 'preset' && !!avatarPresetKey) ||
			(avatarKind === 'custom' && !!avatarUrl && !!avatarAssetId);
		submitEnabled =
			joinCode.length === 5 &&
			name.trim().length > 0 &&
			hasAvatar &&
			!uploadingAvatar &&
			!validatingProfile;
	});

	$effect(() => {
		$playerProfile = normalizePlayerProfile({
			name,
			avatar_kind: avatarKind,
			avatar_preset_key: avatarPresetKey,
			avatar_url: avatarUrl,
			avatar_asset_id: avatarAssetId
		});
	});

	onMount(() => {
		validateStoredAvatar();
	});

	onDestroy(() => {
		clearPendingImage();
	});
</script>

<svelte:head>
	<title>{$messages.join.title} | {$messages.common.appName}</title>
</svelte:head>

<h1 class="page-title">{$messages.join.title}</h1>
<p class="page-subtitle">{$messages.join.subtitle}</p>

<form onsubmit={onSubmit} class="stack-lg mx-auto mt-8 max-w-3xl">
	<section class="card profile-card">
		<button
			type="button"
			class={`profile-preview text-left ${avatarPickerOpen ? 'profile-preview-open' : ''}`}
			onclick={() => (avatarPickerOpen = !avatarPickerOpen)}
		>
			<Avatar
				name={name.trim() || $messages.join.playerFallback}
				{avatarKind}
				{avatarPresetKey}
				{avatarUrl}
				sizeClass="h-24 w-24"
			/>
			<div class="min-w-0 flex-1">
				<p class="label-title mb-2">{$messages.join.avatar}</p>
				<p class="theme-text text-xl font-black">
					{name.trim() || $messages.join.playerFallback}
				</p>
				<p class="theme-text-muted text-sm">
					{avatarKind === 'custom'
						? $messages.join.customPhotoAvatar
						: `${$messages.join.preset}: ${getAvatarPreset(avatarPresetKey)?.label ?? $messages.join.random}`}
				</p>
				<p class="mt-2 text-sm font-semibold" style="color: var(--party-primary-strong)">
					{avatarPickerOpen ? $messages.join.hideAvatarOptions : $messages.join.changeAvatar}
				</p>
			</div>
		</button>

		<label class="input-wrap">
			<span class="label-title">{$messages.join.name}</span>
			<input
				bind:value={name}
				class="input"
				title={$messages.join.name}
				type="text"
				placeholder={$messages.join.namePlaceholder}
			/>
		</label>

		{#if avatarPickerOpen}
			<div class="stack-md">
				<div>
					<p class="label-title mb-3">{$messages.join.choosePresetAvatar}</p>
					<div class="preset-grid">
						{#each AVATAR_PRESETS as preset (preset.key)}
							<button
								type="button"
								class={`preset-option ${avatarKind === 'preset' && avatarPresetKey === preset.key ? 'selected' : ''}`}
								onclick={() => setPresetAvatar(preset.key)}
							>
								<Avatar
									name={name.trim() || preset.label}
									avatarKind="preset"
									avatarPresetKey={preset.key}
									sizeClass="h-16 w-16"
								/>
								<span>{preset.label}</span>
							</button>
						{/each}
					</div>
				</div>

				<div class="card upload-card">
					<div class="flex items-start justify-between gap-4">
						<div>
							<p class="label-title">{$messages.join.takePhotoOrChoose}</p>
							<p class="theme-text-muted mt-1 text-sm">{$messages.join.photoHelp}</p>
						</div>
						<label class="btn btn-secondary cursor-pointer">
							{$messages.join.useCameraPhoto}
							<input
								class="sr-only"
								type="file"
								accept="image/*"
								capture="user"
								onchange={onAvatarFileSelected}
							/>
						</label>
					</div>

					{#if pendingImageUrl}
						<div class="mt-5 grid gap-4 md:grid-cols-[auto_1fr] md:items-start">
							<AvatarCropEditor bind:this={cropEditor} imageUrl={pendingImageUrl} />
							<div class="stack-md">
								<p class="theme-text-muted text-sm">{$messages.join.adjustPhoto}</p>
								<div class="flex flex-wrap gap-3">
									<button
										type="button"
										class="btn btn-accent"
										disabled={uploadingAvatar}
										onclick={uploadCustomAvatar}
									>
										{uploadingAvatar ? $messages.join.uploading : $messages.join.useThisPhoto}
									</button>
									<button type="button" class="btn btn-ghost" onclick={clearPendingImage}>
										{$messages.common.cancel}
									</button>
								</div>
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</section>

	<section class="card">
		<label class="input-wrap">
			<span class="label-title">{$messages.join.joinCode}</span>
			<input
				use:uppercase
				bind:value={joinCode}
				class="input text-center text-4xl tracking-[0.25em]"
				title={$messages.join.joinCode}
				type="text"
				placeholder={$messages.join.joinCodePlaceholder}
			/>
		</label>

		{#if validatingProfile}
			<p class="theme-text-muted mt-4 text-sm">{$messages.join.checkingSavedAvatar}</p>
		{/if}

		<button disabled={!submitEnabled} type="submit" class="btn btn-accent mt-6 w-full text-4xl">
			{$messages.join.joinAction}
		</button>
	</section>
</form>

<style>
	.profile-card {
		display: grid;
		gap: 1.5rem;
	}

	.profile-preview {
		display: flex;
		align-items: center;
		gap: 1rem;
		width: 100%;
		padding: 1rem 1.1rem;
		border-radius: 1.35rem;
		border: 1px solid color-mix(in srgb, var(--party-primary), var(--party-border) 60%);
		background: linear-gradient(
			135deg,
			color-mix(in srgb, var(--party-accent), var(--party-surface-strong) 90%),
			color-mix(in srgb, var(--party-primary), var(--party-surface-strong) 90%)
		);
		color: var(--party-ink);
		transition:
			transform 150ms ease,
			box-shadow 150ms ease,
			border-color 150ms ease;
	}

	.profile-preview:hover {
		transform: translateY(-1px);
	}

	.profile-preview-open {
		border-color: var(--party-primary);
		box-shadow: 0 16px 30px color-mix(in srgb, var(--party-primary), transparent 84%);
	}

	.preset-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(7rem, 1fr));
		gap: 0.85rem;
	}

	.preset-option {
		display: grid;
		justify-items: center;
		gap: 0.65rem;
		padding: 0.9rem 0.75rem;
		border-radius: 1.25rem;
		border: 1px solid var(--party-border);
		background: var(--party-surface-strong);
		font-weight: 800;
		color: var(--party-ink);
		transition:
			transform 150ms ease,
			border-color 150ms ease,
			box-shadow 150ms ease;
	}

	.preset-option:hover {
		transform: translateY(-1px);
	}

	.preset-option.selected {
		border-color: var(--party-soft-primary-border);
		background: var(--party-soft-primary-bg);
		box-shadow: 0 16px 30px color-mix(in srgb, var(--party-primary), transparent 82%);
	}

	.upload-card {
		background: linear-gradient(
			135deg,
			color-mix(in srgb, var(--party-primary), var(--party-surface-strong) 92%),
			var(--party-surface-strong)
		);
	}

	@media (max-width: 640px) {
		.profile-preview {
			align-items: flex-start;
		}
	}
</style>
