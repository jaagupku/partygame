<script lang="ts">
	import { messages } from '$lib/i18n';
	import type { DecorationSurface } from '../registry';
	let { variant, surface }: { variant: string; surface: DecorationSurface } = $props();
</script>

{#if surface === 'preview'}
	<div class="store-window" aria-hidden="true">
		<img src="/presentation/price/storefront.svg" alt="" width="720" height="300" />
	</div>
{:else if variant === 'welcome'}
	<div class="store-welcome">
		<p class="store-eyebrow">{$messages.priceStore.welcome}</p>
		<img src="/presentation/price/storefront.svg" alt="" width="720" height="300" />
	</div>
{:else}
	<div class="store-corner" aria-hidden="true">
		<img src="/presentation/price/shopping-bag.svg" alt="" width="160" height="200" />
	</div>
{/if}
