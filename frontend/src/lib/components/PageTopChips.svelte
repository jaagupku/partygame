<script lang="ts">
	import { goto } from '$app/navigation';

	import { locale, locales, messages } from '$lib/i18n';
</script>

<div class="page-top-chips">
	<button class="chip-button" onclick={() => goto('/definitions')}>
		{$messages.common.manageDefinitions}
	</button>

	<label class="chip-select">
		<span class="sr-only">{$messages.common.language}</span>
		<select bind:value={$locale} aria-label={$messages.common.language}>
			{#each locales as option}
				<option value={option.code}>{option.label}</option>
			{/each}
		</select>
	</label>
</div>
