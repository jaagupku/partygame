<script lang="ts">
	import 'iconify-icon';
	import { messages } from '$lib/i18n';
	import { CONTROLLER_REACTIONS, type ReactionEmoji, type ReactionOption } from '$lib/reactions.js';

	interface ReactionBarProps {
		connected: boolean;
		onReact: (reaction: ReactionEmoji) => void;
	}

	let { connected, onReact }: ReactionBarProps = $props();
	let selectedReaction = $state<ReactionOption>(CONTROLLER_REACTIONS[0]);
	let chooserOpen = $state(false);

	function sendSelectedReaction() {
		if (!connected) {
			return;
		}
		onReact(selectedReaction.emoji);
	}

	function selectReaction(reaction: ReactionOption) {
		if (!connected) {
			return;
		}
		selectedReaction = reaction;
		chooserOpen = false;
		onReact(reaction.emoji);
	}

	function toggleChooser() {
		if (!connected) {
			return;
		}
		chooserOpen = !chooserOpen;
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			chooserOpen = false;
		}
	}

	function viewportPortal(node: HTMLElement) {
		document.body.appendChild(node);
		return {
			destroy() {
				node.remove();
			}
		};
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<section use:viewportPortal class="reaction-dock" aria-label={$messages.gameplay.reactionBarTitle}>
	{#if chooserOpen}
		<div class="reaction-menu" role="menu" aria-label={$messages.gameplay.chooseReaction}>
			{#each CONTROLLER_REACTIONS as reaction}
				<button
					type="button"
					class="reaction-option"
					class:selected={reaction.id === selectedReaction.id}
					role="menuitem"
					disabled={!connected}
					onclick={() => selectReaction(reaction)}
					aria-label={$messages.gameplay.reactionLabels[reaction.id]}
					title={$messages.gameplay.reactionLabels[reaction.id]}
				>
					{reaction.emoji}
				</button>
			{/each}
		</div>
	{/if}

	<div class="reaction-buttons">
		<button
			type="button"
			class="reaction-primary"
			disabled={!connected}
			onclick={sendSelectedReaction}
			aria-label={$messages.gameplay.sendSelectedReaction(
				$messages.gameplay.reactionLabels[selectedReaction.id]
			)}
			title={$messages.gameplay.reactionBarHelp}
		>
			{selectedReaction.emoji}
		</button>
		<button
			type="button"
			class="reaction-chooser"
			class:active={chooserOpen}
			disabled={!connected}
			onclick={toggleChooser}
			aria-label={$messages.gameplay.chooseReaction}
			aria-expanded={chooserOpen}
			title={$messages.gameplay.chooseReaction}
		>
			<iconify-icon icon={chooserOpen ? 'fluent:chevron-down-16-filled' : 'fluent:emoji-16-filled'}
			></iconify-icon>
		</button>
	</div>
</section>

<style>
	.reaction-dock {
		position: fixed;
		right: max(0.5rem, env(safe-area-inset-right));
		bottom: max(0.5rem, env(safe-area-inset-bottom));
		z-index: 70;
		display: grid;
		justify-items: end;
		gap: 0.55rem;
		pointer-events: none;
	}

	.reaction-menu,
	.reaction-buttons {
		pointer-events: auto;
	}

	.reaction-menu {
		display: grid;
		grid-template-columns: repeat(3, 3.25rem);
		gap: 0.45rem;
		border: 1px solid rgba(148, 163, 184, 0.28);
		border-radius: 1rem;
		background: rgba(255, 255, 255, 0.95);
		padding: 0.55rem;
		box-shadow: 0 18px 42px rgba(15, 23, 42, 0.2);
		backdrop-filter: blur(12px);
	}

	.reaction-buttons {
		display: flex;
		align-items: end;
		gap: 0.45rem;
	}

	.reaction-primary,
	.reaction-chooser,
	.reaction-option {
		display: grid;
		place-items: center;
		border: 1px solid rgba(15, 23, 42, 0.1);
		background: rgb(255, 255, 255);
		box-shadow: 0 10px 26px rgba(15, 23, 42, 0.16);
		transition:
			transform 120ms ease,
			box-shadow 120ms ease,
			opacity 120ms ease;
	}

	.reaction-primary {
		width: 4.35rem;
		height: 4.35rem;
		border-radius: 999px;
		font-size: 2.45rem;
	}

	.reaction-chooser {
		width: 2.75rem;
		height: 2.75rem;
		border-radius: 999px;
		color: rgb(15, 23, 42);
		font-size: 1.35rem;
	}

	.reaction-option {
		width: 3.25rem;
		height: 3.25rem;
		border-radius: 0.85rem;
		font-size: 1.85rem;
	}

	.reaction-primary:not(:disabled):active,
	.reaction-chooser:not(:disabled):active,
	.reaction-option:not(:disabled):active {
		transform: translateY(1px) scale(0.96);
	}

	.reaction-primary:disabled,
	.reaction-chooser:disabled,
	.reaction-option:disabled {
		cursor: not-allowed;
		opacity: 0.45;
	}

	.reaction-chooser.active,
	.reaction-option.selected {
		border-color: rgba(14, 165, 233, 0.42);
		background: rgb(224, 242, 254);
		box-shadow: 0 10px 26px rgba(14, 165, 233, 0.18);
	}

	@media (hover: hover) {
		.reaction-primary:not(:disabled):hover,
		.reaction-chooser:not(:disabled):hover,
		.reaction-option:not(:disabled):hover {
			transform: translateY(-1px);
			box-shadow: 0 14px 30px rgba(15, 23, 42, 0.2);
		}
	}

	@media (max-width: 640px) {
		.reaction-dock {
			right: max(0.35rem, env(safe-area-inset-right));
			bottom: max(0.35rem, env(safe-area-inset-bottom));
			gap: 0.35rem;
		}

		.reaction-buttons {
			gap: 0.3rem;
		}

		.reaction-primary {
			width: 3.65rem;
			height: 3.65rem;
			font-size: 2.05rem;
		}

		.reaction-chooser {
			width: 2.25rem;
			height: 2.25rem;
			font-size: 1.1rem;
		}

		.reaction-menu {
			grid-template-columns: repeat(3, 2.7rem);
			gap: 0.35rem;
			border-radius: 0.85rem;
			padding: 0.4rem;
		}

		.reaction-option {
			width: 2.7rem;
			height: 2.7rem;
			border-radius: 0.75rem;
			font-size: 1.45rem;
		}
	}
</style>
