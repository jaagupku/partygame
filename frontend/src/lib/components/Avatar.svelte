<script lang="ts">
	import { getAvatarSrc } from '$lib/avatar-presets.js';

	interface AvatarProps {
		name: string;
		avatarKind?: string | null;
		avatarPresetKey?: string | null;
		avatarUrl?: string | null;
		sizeClass?: string;
		className?: string;
	}

	let {
		name,
		avatarKind = null,
		avatarPresetKey = null,
		avatarUrl = null,
		sizeClass = 'h-12 w-12',
		className = ''
	}: AvatarProps = $props();

	const src = $derived(getAvatarSrc(avatarKind, avatarPresetKey, avatarUrl));
	const initials = $derived(
		name
			.trim()
			.split(/\s+/)
			.slice(0, 2)
			.map((part) => part.charAt(0).toUpperCase())
			.join('') || '?'
	);
</script>

<div class={`avatar-shell ${sizeClass} ${className}`} aria-label={`Avatar for ${name}`} role="img">
	{#if src}
		<img class="avatar-image" {src} alt={`Avatar for ${name}`} />
	{:else}
		<span class="avatar-fallback">{initials}</span>
	{/if}
</div>

<style>
	.avatar-shell {
		display: grid;
		place-items: center;
		flex: none;
		overflow: hidden;
		border-radius: 999px;
		background:
			radial-gradient(circle at top, rgb(255 255 255 / 0.9), rgb(255 255 255 / 0.4)),
			linear-gradient(135deg, #dbeafe, #fef3c7);
		border: 2px solid rgb(255 255 255 / 0.9);
		box-shadow: 0 10px 25px rgb(15 23 42 / 0.12);
	}

	.avatar-image {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.avatar-fallback {
		font-size: 0.95rem;
		font-weight: 900;
		letter-spacing: 0.08em;
		color: #0f172a;
	}
</style>
