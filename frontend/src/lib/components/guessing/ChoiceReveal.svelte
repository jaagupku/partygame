<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import Avatar from '$lib/components/Avatar.svelte';
	import ProductCard from '$lib/components/prices/ProductCard.svelte';
	import { messages } from '$lib/i18n';
	import {
		CHOICE_INTRO_MS,
		choiceHopMs,
		choiceRevealMs,
		choiceStepMs,
		choiceTrays
	} from './guess-reveal';

	let {
		products,
		values,
		correctId,
		results,
		players = [],
		winnerLabel,
		animate = false
	}: {
		products: (PriceCard | CalorieCard)[];
		values: { id: string; value: string; unit?: string }[];
		correctId?: string;
		results: PriceResult[];
		players?: Player[];
		winnerLabel: string;
		animate?: boolean;
	} = $props();

	const POP_MS = 220;
	const SQUASH_MS = 160;
	const ARC_POINTS = 10;

	// Only a live phase change animates; reconnects, history and reduced motion show the result.
	const playing = untrack(
		() =>
			animate &&
			!(
				typeof window !== 'undefined' &&
				window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
			)
	);
	let revealed = $state(!playing);
	let root: HTMLElement;

	const productIds = $derived(products.map((product) => product.id));
	const grouped = $derived(choiceTrays(results, productIds));
	const missing = $derived(new Set(grouped.pool.map((result) => result.player_id)));
	// Everyone starts in the lineup; once placed, only players without an answer stay there.
	const lineup = $derived(playing ? results : grouped.pool);
	const playerById = $derived(new Map(players.map((player) => [player.id, player])));
	const avatarSize = (count: number) =>
		count <= 8 ? 'h-16 w-16' : count <= 16 ? 'h-12 w-12' : 'h-9 w-9';
	const lineupSize = (count: number) =>
		count <= 8 ? 'h-20 w-20' : count <= 16 ? 'h-14 w-14' : 'h-10 w-10';
	const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

	/** Avatar centre and width, so the hop lines up faces rather than name labels. */
	function face(element: HTMLElement) {
		const rect = (element.querySelector('.avatar-shell') ?? element).getBoundingClientRect();
		return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2, width: rect.width };
	}

	onMount(() => {
		if (!playing) return;
		const byPlayer = (selector: string) =>
			new Map(
				[...root.querySelectorAll<HTMLElement>(selector)].map((element) => [
					element.dataset.player,
					element
				])
			);
		const slots = byPlayer('.choice-slot');
		const seats = byPlayer('.choice-option .choice-player');
		const waiting = byPlayer('.choice-lineup .choice-player');
		const movers = results.filter((result) => !missing.has(result.player_id));
		const step = choiceStepMs(movers.length);
		const hop = choiceHopMs(movers.length);
		const popStagger = Math.min(50, 300 / Math.max(1, results.length - 1));
		const animations: Animation[] = [];
		const play = (element: Element, keyframes: Keyframe[], options: KeyframeAnimationOptions) => {
			if (typeof element.animate === 'function')
				animations.push(element.animate(keyframes, options));
		};

		results.forEach((result, index) => {
			const popAt = index * popStagger;
			const stay = waiting.get(result.player_id);
			if (stay) {
				play(
					stay,
					[
						{ transform: 'scale(0.3)', opacity: 0 },
						{ transform: 'none', opacity: 1 }
					],
					{ duration: POP_MS, delay: popAt, easing: 'ease-out', fill: 'backwards' }
				);
				return;
			}
			const element = seats.get(result.player_id);
			const slot = slots.get(result.player_id);
			if (!element || !slot) return;
			const from = face(slot);
			const to = face(element);
			const dx = from.x - to.x;
			const dy = from.y - to.y;
			const scale = to.width ? from.width / to.width : 1;
			// Scale around the face so the hop lands it exactly on its seat.
			const shell = element.querySelector<HTMLElement>('.avatar-shell');
			element.style.transformOrigin = `50% ${(shell?.offsetTop ?? 0) + (shell?.offsetHeight ?? 0) / 2}px`;

			const moveAt = CHOICE_INTRO_MS + movers.indexOf(result) * step;
			const landAt = moveAt + hop;
			const duration = landAt + SQUASH_MS;
			const at = (ms: number) => ms / duration;
			const pose = (x: number, y: number, size: number) =>
				`translate(${x}px, ${y}px) scale(${size})`;
			const arc = 36 + Math.abs(dx) * 0.12;
			const flight: Keyframe[] = [];
			for (let i = 1; i < ARC_POINTS; i++) {
				const u = i / ARC_POINTS;
				const t = easeInOut(u);
				const lift = 4 * t * (1 - t);
				flight.push({
					offset: at(moveAt + hop * u),
					transform: pose(
						dx * (1 - t),
						dy * (1 - t) - arc * lift,
						(scale + (1 - scale) * t) * (1 + 0.18 * lift)
					)
				});
			}
			play(
				element,
				[
					{ offset: 0, transform: pose(dx, dy, scale * 0.3), opacity: 0 },
					{ offset: at(popAt + POP_MS), transform: pose(dx, dy, scale), opacity: 1 },
					{ offset: at(moveAt), transform: pose(dx, dy, scale), opacity: 1 },
					...flight,
					{ offset: at(landAt), transform: 'scale(1.18, 0.82)', opacity: 1 },
					{ offset: 1, transform: 'none', opacity: 1 }
				],
				{ duration, fill: 'backwards' }
			);
			const card = element.closest('.choice-option')?.querySelector('.choice-card');
			if (card)
				play(
					card,
					[
						{ transform: 'none' },
						{ transform: 'translateY(4px) scale(1.01)' },
						{ transform: 'none' }
					],
					{ duration: 200, delay: landAt, easing: 'ease-out' }
				);
		});
		const timer = setTimeout(() => (revealed = true), choiceRevealMs(results, productIds));
		return () => {
			clearTimeout(timer);
			for (const animation of animations) animation.cancel();
		};
	});
</script>

{#snippet person(result: PriceResult, size: string, named: boolean)}
	{@const player = playerById.get(result.player_id)}
	<Avatar
		name={result.player_name}
		avatarKind={player?.avatar_kind}
		avatarPresetKey={player?.avatar_preset_key}
		avatarUrl={player?.avatar_url}
		sizeClass={size}
	/>
	{#if named}<span class="choice-player-name">{result.player_name}</span>{/if}
{/snippet}

<div class="choice-reveal" class:choice-revealed={revealed} bind:this={root}>
	{#if lineup.length}
		<div class="choice-lineup">
			<ul class="choice-lineup-row">
				{#each lineup as result (result.player_id)}
					{#if missing.has(result.player_id)}
						<li
							class="choice-player"
							class:choice-player-missing={revealed}
							data-player={result.player_id}
						>
							{@render person(result, lineupSize(lineup.length), lineup.length <= 12)}
						</li>
					{:else}
						<!-- Invisible seat in the lineup; the avatar itself already sits in its tray. -->
						<li class="choice-slot" data-player={result.player_id} aria-hidden="true">
							{@render person(result, lineupSize(lineup.length), lineup.length <= 12)}
						</li>
					{/if}
				{/each}
			</ul>
			{#if grouped.pool.length}<p class="choice-pool-label" aria-hidden={!revealed}>
					{$messages.priceGame.noAnswer}
				</p>{/if}
		</div>
	{/if}
	{#each products as product (product.id)}
		{@const value = values.find((item) => item.id === product.id)}
		{@const chosen = grouped.trays.get(product.id) ?? []}
		{@const correct = product.id === correctId}
		<section
			class="choice-option"
			class:choice-correct={revealed && correct}
			class:choice-wrong={revealed && !correct}
			aria-label={product.title}
		>
			<ul class="choice-tray">
				{#each chosen as result (result.player_id)}
					<li class="choice-player" data-player={result.player_id}>
						{@render person(result, avatarSize(chosen.length), chosen.length <= 10)}
					</li>
				{/each}
			</ul>
			<div class="choice-card">
				<p class="choice-ribbon" aria-hidden={!revealed || !correct}>{winnerLabel}</p>
				<ProductCard {product} stage />
				{#if value}<p class="choice-value" aria-hidden={!revealed}>
						<strong>{value.value}</strong>{#if value.unit}{' '}<span>{value.unit}</span>{/if}
					</p>{/if}
			</div>
		</section>
	{/each}
</div>

<style>
	.choice-reveal {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		align-items: end;
		gap: 1rem clamp(1rem, 4vw, 4rem);
	}
	.choice-lineup {
		grid-column: 1 / -1;
		display: grid;
		justify-items: center;
		gap: 0.25rem;
	}
	.choice-lineup-row {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		align-items: start;
		gap: 0.75rem;
		max-width: min(100%, 48rem);
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.choice-slot {
		display: grid;
		justify-items: center;
		gap: 0.2rem;
		max-width: 6rem;
		visibility: hidden;
	}
	.choice-option {
		display: grid;
		gap: 0.75rem;
		min-width: 0;
		transition:
			opacity 300ms ease-out,
			filter 300ms ease-out;
	}
	.choice-wrong {
		opacity: 0.5;
		filter: saturate(0.4);
	}
	.choice-tray {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		align-items: end;
		gap: 0.5rem;
		min-height: 4.5rem;
		margin: 0;
		padding: 0.25rem;
		list-style: none;
	}
	.choice-player {
		display: grid;
		justify-items: center;
		gap: 0.2rem;
		max-width: 6rem;
		position: relative;
		z-index: 1;
		will-change: transform;
	}
	.choice-player-name {
		max-width: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: 0.8rem;
		font-weight: 800;
	}
	.choice-correct .choice-player :global(.avatar-shell) {
		outline: 4px solid var(--party-accent);
		outline-offset: 2px;
		animation: choice-bounce 420ms ease-out;
	}
	.choice-card {
		display: grid;
		gap: 0.5rem;
	}
	.choice-ribbon,
	.choice-value {
		visibility: hidden;
		opacity: 0;
		transition: opacity 250ms ease-out;
	}
	.choice-correct .choice-ribbon,
	.choice-revealed .choice-value {
		visibility: visible;
		opacity: 1;
	}
	/* In flow, so the tag never covers compact product titles. */
	.choice-ribbon {
		justify-self: center;
		padding: 0.3rem 1rem;
		border-radius: 999px;
		background: var(--party-accent);
		color: var(--party-ink);
		font-weight: 900;
		white-space: nowrap;
	}
	.choice-value {
		text-align: center;
		font-variant-numeric: tabular-nums;
	}
	.choice-value strong {
		font-size: clamp(2rem, 4vw, 4rem);
		font-weight: 900;
		line-height: 1.1;
	}
	.choice-pool-label {
		font-size: 0.75rem;
		font-weight: 800;
		text-align: center;
		opacity: 0.7;
		transition: opacity 250ms ease-out;
	}
	.choice-pool-label[aria-hidden='true'] {
		opacity: 0;
	}
	.choice-player-missing {
		opacity: 0.6;
		filter: grayscale(0.6);
		transition:
			opacity 250ms ease-out,
			filter 250ms ease-out;
	}
	@media (max-width: 639px) {
		.choice-reveal {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	@keyframes choice-bounce {
		40% {
			transform: translateY(-0.4rem);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.choice-option,
		.choice-ribbon,
		.choice-value,
		.choice-pool-label,
		.choice-player-missing {
			transition: none;
		}
		.choice-correct .choice-player :global(.avatar-shell) {
			animation: none;
		}
	}
</style>
