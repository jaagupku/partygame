<script lang="ts">
	import { messages } from '$lib/i18n';
	import { CONTROLLER_REACTIONS, type ReactionEmoji } from '$lib/reactions.js';

	interface ReactionBarProps {
		connected: boolean;
		onReact: (reaction: ReactionEmoji) => void;
	}

	let { connected, onReact }: ReactionBarProps = $props();
</script>

<section class="card stack-md">
	<div class="flex items-center justify-between gap-3">
		<div>
			<h2 class="label-title text-2xl">{$messages.gameplay.reactionBarTitle}</h2>
			<p class="text-sm text-slate-600">{$messages.gameplay.reactionBarHelp}</p>
		</div>
		<span class="badge bg-amber-100 text-amber-800">{$messages.common.live}</span>
	</div>
	<div class="grid grid-cols-3 gap-3 sm:grid-cols-6">
		{#each CONTROLLER_REACTIONS as reaction}
			<button
				type="button"
				class="btn btn-ghost min-h-16 text-4xl"
				disabled={!connected}
				onclick={() => onReact(reaction.emoji)}
				aria-label={$messages.gameplay.reactionLabels[reaction.id]}
				title={$messages.gameplay.reactionLabels[reaction.id]}
			>
				{reaction.emoji}
			</button>
		{/each}
	</div>
</section>
