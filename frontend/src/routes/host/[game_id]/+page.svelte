<script lang="ts">
	import { browser } from '$app/environment';
	import { onDestroy, onMount } from 'svelte';
	import Avatar from '$lib/components/Avatar.svelte';
	import GameConnectionStatus from '$lib/components/GameConnectionStatus.svelte';
	import FinaleDisplay from '$lib/components/endgame/FinaleDisplay.svelte';
	import ReactionBurstOverlay from '$lib/components/host/ReactionBurstOverlay.svelte';
	import Scoreboard from '$lib/components/host/Scoreboard.svelte';
	import StepDisplayPreview from '$lib/components/StepDisplayPreview.svelte';
	import { createGameStore } from '$lib/game-store.js';
	import { connectionLabel, formatPlayerStatus, messages, onOffLabel, pageTitle } from '$lib/i18n';
	import { createReconnectingWebSocket } from '$lib/reconnecting-websocket.js';

	const { data } = $props();
	const lobby = () => data.lobby;
	const SAFETY_RESYNC_INTERVAL_MS = 120_000;
	const definitionTitle = () =>
		data.definitionTitle || data.lobby.definition_id || $messages.definitions.untitledDefinition;

	const game = createGameStore(lobby());
	let isConnected = $state(false);
	let socket: ReturnType<typeof createReconnectingWebSocket> | null = null;
	let resyncPending = $state(false);
	let resyncIntervalId = $state<number | null>(null);
	const playerMap = $derived(new Map($game.players.map((player) => [player.id, player])));
	const buzzedPlayerName = $derived(
		$game.buzzedPlayerId ? (playerMap.get($game.buzzedPlayerId)?.name ?? '') : ''
	);
	const countdown = $derived(
		Math.max(0, Math.ceil($game.activeStep?.timer.remaining_seconds ?? 0))
	);
	const MAX_ACTIVE_REACTIONS = 36;

	type ActiveReaction = {
		instanceId: string;
		reaction: string;
		xPercent: number;
		driftX: number;
		sizeRem: number;
		rotationDeg: number;
		durationMs: number;
		delayMs: number;
		expiresAt: number;
	};

	let activeReactions = $state<ActiveReaction[]>([]);
	let lastReactionInstanceId = $state<string | undefined>(undefined);
	let reactionCleanupIntervalId = $state<number | null>(null);

	function addReactionEffect(event: PlayerReactionEvent) {
		const durationMs = 2600 + Math.random() * 1200;
		const nextReaction: ActiveReaction = {
			instanceId: event.instance_id,
			reaction: event.reaction,
			xPercent: 10 + Math.random() * 80,
			driftX: -120 + Math.random() * 240,
			sizeRem: 2.1 + Math.random() * 1.4,
			rotationDeg: -16 + Math.random() * 32,
			durationMs,
			delayMs: Math.random() * 120,
			expiresAt: Date.now() + durationMs + 500
		};
		activeReactions = [...activeReactions.slice(-(MAX_ACTIVE_REACTIONS - 1)), nextReaction];
	}

	function cleanupExpiredReactions() {
		const now = Date.now();
		activeReactions = activeReactions.filter((entry) => entry.expiresAt > now);
	}

	$effect(() => {
		const reaction = $game.lastReaction;
		if (!reaction || reaction.instance_id === lastReactionInstanceId) {
			return;
		}
		lastReactionInstanceId = reaction.instance_id;
		addReactionEffect(reaction);
	});

	onMount(() => {
		if (!browser) {
			return;
		}
		const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
		socket = createReconnectingWebSocket(
			`${protocol}://${window.location.host}/api/v1/game/${lobby().id}/host`,
			{
				onMessage: (data) => {
					const result = game.onMessage(data);
					if (result === 'resync_required') {
						requestResync();
					} else if (result === 'snapshot_applied') {
						resyncPending = false;
					}
				},
				onStatusChange: (connected) => {
					isConnected = connected;
					if (!connected) {
						resyncPending = false;
					}
				}
			}
		);
		resyncIntervalId = window.setInterval(() => {
			if (isConnected) {
				requestResync();
			}
		}, SAFETY_RESYNC_INTERVAL_MS);
		reactionCleanupIntervalId = window.setInterval(() => {
			cleanupExpiredReactions();
		}, 500);
		return () => {
			if (resyncIntervalId !== null) {
				clearInterval(resyncIntervalId);
				resyncIntervalId = null;
			}
			if (reactionCleanupIntervalId !== null) {
				clearInterval(reactionCleanupIntervalId);
				reactionCleanupIntervalId = null;
			}
			socket?.close();
			socket = null;
		};
	});

	onDestroy(() => {
		if (resyncIntervalId !== null) {
			clearInterval(resyncIntervalId);
			resyncIntervalId = null;
		}
		if (reactionCleanupIntervalId !== null) {
			clearInterval(reactionCleanupIntervalId);
			reactionCleanupIntervalId = null;
		}
		socket?.close();
		socket = null;
	});

	function requestResync() {
		if (resyncPending) {
			return;
		}
		const sent = socket?.send(
			JSON.stringify({
				type_: 'resync_request',
				last_revision: $game.lastRevision
			})
		);
		if (sent) {
			resyncPending = true;
		}
	}

	function setHost(playerId: string) {
		socket?.send(
			JSON.stringify({
				type_: 'set_host',
				player_id: playerId
			})
		);
	}
</script>

<svelte:head>
	<title>{pageTitle(`${definitionTitle()} | ${$messages.hostView.hostLobbyTitle}`)}</title>
</svelte:head>

{#if $game.state === 'waiting_for_players'}
	<h1 class="page-title">{definitionTitle()}</h1>
	<p class="page-subtitle">
		{$messages.hostView.joinCode}:
		<span class="mt-2 block text-5xl font-black tracking-[0.28em] text-slate-950 sm:text-6xl">
			{$game.join_code}
		</span>
	</p>
	<p class="page-subtitle mt-2">
		{$messages.hostView.hostMode}: <span class="font-bold">{onOffLabel($game.host_enabled)}</span>
	</p>
	<p class="page-subtitle mt-2">{$messages.hostView.useHostController}</p>
	<GameConnectionStatus
		connected={isConnected}
		connectionLabel={connectionLabel(isConnected)}
		showInline={false}
		showDisconnectedChip={true}
	/>

	{#if $game.players.length > 0}
		<ul class="stack-md mt-8">
			{#each $game.players as player}
				<li class="card flex items-center justify-between gap-3">
					<button
						type="button"
						class="flex min-w-0 items-center gap-3 text-left text-xl font-bold text-slate-800 transition-opacity hover:opacity-75"
						onclick={() => setHost(player.id)}
					>
						<Avatar
							name={player.name}
							avatarKind={player.avatar_kind}
							avatarPresetKey={player.avatar_preset_key}
							avatarUrl={player.avatar_url}
						/>
						<span class="truncate">{player.name}</span>
					</button>
					<div class="flex items-center gap-2">
						{#if player.isHost}
							<span class="badge bg-sky-100 text-sky-700">{$messages.common.host}</span>
						{/if}
						<span class="text-sm text-slate-600">{formatPlayerStatus(player.status)}</span>
					</div>
				</li>
			{/each}
		</ul>
	{/if}
{:else}
	<div class="relative h-full min-h-0 overflow-hidden">
		<section class="relative h-full min-w-0 min-h-0 mt0">
			{#if $game.endGame?.revealed}
				<FinaleDisplay
					endGame={$game.endGame}
					players={$game.players}
					{playerMap}
					title={definitionTitle()}
					connected={isConnected}
					connectionLabel={connectionLabel(isConnected)}
					showDisconnectedChip={true}
				/>
			{:else if $game.phase === 'finished' && $game.endGame}
				<section
					class="card grid h-full min-h-0 place-items-center overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.95),_rgba(219,234,254,0.88)_45%,_rgba(240,253,244,0.92))] text-center"
				>
					<div class="max-w-2xl">
						<h1 class="page-title text-4xl md:text-5xl">{definitionTitle()}</h1>
						<p class="page-subtitle mt-4">{$messages.hostView.finalResultsReady}</p>
						<GameConnectionStatus
							connected={isConnected}
							connectionLabel={connectionLabel(isConnected)}
							showInline={false}
							showDisconnectedChip={true}
						/>
					</div>
				</section>
			{:else}
				<StepDisplayPreview
					step={$game.activeStep}
					revealedSubmission={$game.revealedSubmission}
					revealedAnswer={$game.revealedAnswer}
					buzzerActive={$game.buzzerActive}
					buzzedPlayerId={$game.buzzedPlayerId}
					{buzzedPlayerName}
					displayPhase={$game.displayPhase}
					phaseLabel={$game.phase ?? 'question_active'}
					connected={isConnected}
					connectionLabel={connectionLabel(isConnected)}
					layoutMode="host-stage"
					showDisconnectedChip={true}
					{countdown}
				/>
			{/if}
			<ReactionBurstOverlay
				reactions={activeReactions}
				label={$messages.gameplay.reactionBurstOverlayLabel}
			/>
		</section>

		<aside
			class={`pointer-events-none absolute inset-y-0 right-0 z-10 w-[min(30rem,38vw)] max-w-full p-3 transition-transform duration-300 ease-out ${
				$game.scoreboardVisible ? 'translate-x-0' : 'translate-x-[calc(100%+1rem)]'
			}`}
		>
			{#if !$game.endGame?.revealed}
				<div class="pointer-events-auto h-full">
					<Scoreboard players={$game.players} {playerMap} variant="overlay" />
				</div>
			{/if}
		</aside>
	</div>
{/if}
