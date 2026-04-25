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
	let uploadError = $state('');
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
		uploadError = '';
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
			uploadError =
				typeof body === 'object' && body !== null && 'detail' in body
					? String(body.detail)
					: $messages.join.couldNotJoinGame;
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
		uploadError = '';
		input.value = '';
	}

	async function uploadCustomAvatar() {
		if (!cropEditor) {
			return;
		}
		uploadingAvatar = true;
		uploadError = '';
		try {
			const blob = await cropEditor.exportBlob();
			if (!blob) {
				uploadError = $messages.join.couldNotPrepareAvatar;
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
				uploadError =
					(typeof asset === 'object' && asset !== null && 'detail' in asset && asset.detail) ||
					$messages.join.couldNotUploadAvatar;
				return;
			}
			avatarKind = 'custom';
			avatarPresetKey = null;
			avatarUrl = asset.public_url;
			avatarAssetId = asset.id;
			avatarPickerOpen = false;
			clearPendingImage();
		} catch {
			uploadError = $messages.join.couldNotUploadAvatar;
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
				<p class="text-xl font-black text-slate-900">
					{name.trim() || $messages.join.playerFallback}
				</p>
				<p class="text-sm text-slate-600">
					{avatarKind === 'custom'
						? $messages.join.customPhotoAvatar
						: `${$messages.join.preset}: ${getAvatarPreset(avatarPresetKey)?.label ?? $messages.join.random}`}
				</p>
				<p class="mt-2 text-sm font-semibold text-sky-700">
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
							<p class="mt-1 text-sm text-slate-600">{$messages.join.photoHelp}</p>
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
								<p class="text-sm text-slate-600">{$messages.join.adjustPhoto}</p>
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

					{#if avatarKind === 'custom' && avatarUrl}
						<p class="mt-4 text-sm font-semibold text-emerald-700">
							{$messages.join.customAvatarReady}
						</p>
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

		{#if uploadError}
			<p class="mt-4 text-sm font-semibold text-rose-600">{uploadError}</p>
		{/if}

		{#if validatingProfile}
			<p class="mt-4 text-sm text-slate-600">{$messages.join.checkingSavedAvatar}</p>
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
		border: 1px solid rgb(191 219 254 / 0.7);
		background: linear-gradient(135deg, rgb(255 247 237 / 0.92), rgb(239 246 255 / 0.95));
		transition:
			transform 150ms ease,
			box-shadow 150ms ease,
			border-color 150ms ease;
	}

	.profile-preview:hover {
		transform: translateY(-1px);
	}

	.profile-preview-open {
		border-color: #38bdf8;
		box-shadow: 0 16px 30px rgb(14 165 233 / 0.12);
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
		border: 1px solid rgb(203 213 225 / 0.85);
		background: rgb(255 255 255 / 0.88);
		font-weight: 800;
		color: #0f172a;
		transition:
			transform 150ms ease,
			border-color 150ms ease,
			box-shadow 150ms ease;
	}

	.preset-option:hover {
		transform: translateY(-1px);
	}

	.preset-option.selected {
		border-color: #0ea5e9;
		box-shadow: 0 16px 30px rgb(14 165 233 / 0.14);
	}

	.upload-card {
		background: linear-gradient(135deg, rgb(240 249 255 / 0.95), rgb(248 250 252 / 0.95));
	}

	@media (max-width: 640px) {
		.profile-preview {
			align-items: flex-start;
		}
	}
</style>
