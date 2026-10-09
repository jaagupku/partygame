<script lang="ts">
	import { messages } from '$lib/i18n';
	import type { DecorationSurface } from '../registry';
	let { variant, surface }: { variant: string; surface: DecorationSurface } = $props();
</script>

<!-- Phones omit coach and studio artwork. -->
{#if surface === 'preview' || (surface === 'screen' && variant === 'welcome')}
	<div class="studio-illustration" class:studio-welcome={surface === 'screen'}>
		<img src="/presentation/calorie/studio.svg" alt="" width="720" height="300" />
		{#if surface === 'screen'}<p class="studio-eyebrow">{$messages.calorieStudio.welcome}</p>{/if}
	</div>
{/if}
