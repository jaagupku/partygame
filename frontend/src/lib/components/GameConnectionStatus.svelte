<script lang="ts">
	import { messages } from '$lib/i18n';

	interface Props {
		connected?: boolean | null;
		connectionLabel?: string;
		showInline?: boolean;
		showDisconnectedChip?: boolean;
	}

	let {
		connected = null,
		connectionLabel = '',
		showInline = true,
		showDisconnectedChip = false
	}: Props = $props();

	const normalizedLabel = $derived.by(() => {
		if (connected === true) {
			return $messages.common.live;
		}
		if (connected === false) {
			return $messages.common.disconnected;
		}
		return connectionLabel.trim();
	});
	const isLive = $derived(connected === true);
	const hasLabel = $derived(Boolean(normalizedLabel));
	const showInlineStatus = $derived(showInline && hasLabel && !isLive);
	const showStatusChip = $derived(showDisconnectedChip && hasLabel && !isLive);

	function portal(node: HTMLElement) {
		document.body.appendChild(node);

		return {
			destroy() {
				node.remove();
			}
		};
	}
</script>

{#if showInlineStatus}
	<p class="page-subtitle mt-2">{$messages.common.connection}: {normalizedLabel}</p>
{/if}

{#if showStatusChip}
	<div
		use:portal
		class="fixed bottom-4 left-4 z-20 rounded-full border border-red-200 bg-white/95 px-4 py-2 text-sm font-bold uppercase tracking-[0.16em] text-red-700 shadow-lg shadow-red-100/80 backdrop-blur"
	>
		{normalizedLabel}
	</div>
{/if}
