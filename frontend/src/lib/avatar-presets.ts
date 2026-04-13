export type AvatarSelectionKind = 'preset' | 'custom';

export type LocalPlayerProfile = {
	name: string;
	avatar_kind: AvatarSelectionKind;
	avatar_preset_key: string | null;
	avatar_url: string | null;
	avatar_asset_id: string | null;
};

export type AvatarPreset = {
	key: string;
	label: string;
	src: string;
	accent: string;
};

export const AVATAR_PRESETS: AvatarPreset[] = [
	{ key: 'fox', label: 'Fox', src: '/avatars/fox.svg', accent: '#f97316' },
	{ key: 'otter', label: 'Otter', src: '/avatars/otter.svg', accent: '#0f766e' },
	{ key: 'owl', label: 'Owl', src: '/avatars/owl.svg', accent: '#7c3aed' },
	{ key: 'whale', label: 'Whale', src: '/avatars/whale.svg', accent: '#0284c7' },
	{ key: 'cat', label: 'Cat', src: '/avatars/cat.svg', accent: '#db2777' },
	{ key: 'frog', label: 'Frog', src: '/avatars/frog.svg', accent: '#16a34a' }
];

export const DEFAULT_AVATAR_PRESET_KEY = AVATAR_PRESETS[0].key;

export function createDefaultPlayerProfile(): LocalPlayerProfile {
	return {
		name: '',
		avatar_kind: 'preset',
		avatar_preset_key: DEFAULT_AVATAR_PRESET_KEY,
		avatar_url: null,
		avatar_asset_id: null
	};
}

export function getAvatarPreset(key?: string | null): AvatarPreset | undefined {
	return AVATAR_PRESETS.find((preset) => preset.key === key);
}

export function getAvatarSrc(
	avatarKind?: string | null,
	avatarPresetKey?: string | null,
	avatarUrl?: string | null
): string | null {
	if (avatarKind === 'custom' && avatarUrl) {
		return avatarUrl;
	}
	if (avatarKind === 'preset') {
		return (
			getAvatarPreset(avatarPresetKey)?.src ??
			getAvatarPreset(DEFAULT_AVATAR_PRESET_KEY)?.src ??
			null
		);
	}
	return null;
}

export function normalizePlayerProfile(
	profile?: Partial<LocalPlayerProfile> | null
): LocalPlayerProfile {
	const next = {
		...createDefaultPlayerProfile(),
		...profile
	};
	if (next.avatar_kind === 'custom' && next.avatar_url && next.avatar_asset_id) {
		return next;
	}
	return {
		...next,
		avatar_kind: 'preset',
		avatar_preset_key: getAvatarPreset(next.avatar_preset_key)?.key ?? DEFAULT_AVATAR_PRESET_KEY,
		avatar_url: null,
		avatar_asset_id: null
	};
}
