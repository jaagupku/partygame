<script lang="ts">
	import { messages } from '$lib/i18n';
	import { dismissToast, toasts } from '$lib/toast-store';
</script>

{#if $toasts.length > 0}
	<div class="toast-region" aria-live="polite" aria-label="Notifications">
		{#each $toasts as toast (toast.id)}
			<div class={`toast toast-${toast.tone}`} role={toast.tone === 'error' ? 'alert' : 'status'}>
				<p>{toast.message}</p>
				{#if toast.tone === 'error'}
					<button
						class="toast-close"
						type="button"
						aria-label={$messages.common.close}
						onclick={() => dismissToast(toast.id)}
					>
						x
					</button>
				{/if}
			</div>
		{/each}
	</div>
{/if}

<style lang="postcss">
	.toast-region {
		position: fixed;
		top: 1rem;
		right: 1rem;
		z-index: 80;
		display: grid;
		width: min(24rem, calc(100vw - 2rem));
		gap: 0.75rem;
		pointer-events: none;
	}

	.toast {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		align-items: start;
		gap: 0.75rem;
		padding: 0.85rem 0.95rem;
		border: 1px solid;
		border-radius: 1rem;
		box-shadow: 0 18px 40px rgb(15 23 42 / 0.16);
		font-weight: 800;
		line-height: 1.35;
		pointer-events: auto;
		backdrop-filter: blur(10px);
		animation: toast-in 180ms ease-out;
	}

	.toast-success {
		border-color: var(--party-soft-success-border);
		color: var(--party-soft-success-text);
		background: var(--party-soft-success-bg);
	}

	.toast-status {
		border-color: var(--party-soft-primary-border);
		color: var(--party-soft-primary-text);
		background: var(--party-soft-primary-bg);
	}

	.toast-error {
		border-color: var(--party-soft-danger-border);
		color: var(--party-soft-danger-text);
		background: var(--party-soft-danger-bg);
	}

	.toast-close {
		display: grid;
		width: 1.75rem;
		height: 1.75rem;
		place-items: center;
		border-radius: 999px;
		color: currentColor;
		font-size: 1.35rem;
		line-height: 1;
		transition: background-color 120ms ease;
	}

	.toast-close:hover {
		background: var(--party-muted-control);
	}

	@keyframes toast-in {
		from {
			transform: translateY(-0.35rem);
			opacity: 0;
		}
		to {
			transform: translateY(0);
			opacity: 1;
		}
	}
</style>
