<script lang="ts">
	import { presentationRevision, resolvePresentation, type DecorationSurface } from './registry';
	let {
		gameType,
		variant = 'default',
		surface = 'preview'
	}: { gameType?: string; variant?: string; surface?: DecorationSurface } = $props();
	const profile = $derived.by(() => {
		$presentationRevision;
		return resolvePresentation(gameType);
	});
	const Decoration = $derived(
		profile?.variants?.[variant]?.appearance?.Decoration ?? profile?.appearance.Decoration
	);
</script>

{#if Decoration}<Decoration {variant} {surface} />{/if}
