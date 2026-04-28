<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { createControllerStore } from '$lib/controller-store.js';
	import HostControlsPanel from '$lib/components/controller/HostControlsPanel.svelte';
	import HostReviewQueue from '$lib/components/controller/HostReviewQueue.svelte';
	import GameConnectionStatus from '$lib/components/GameConnectionStatus.svelte';
	import PlayerInputPanel from '$lib/components/controller/PlayerInputPanel.svelte';
	import ReactionBar from '$lib/components/controller/ReactionBar.svelte';
	import FinaleControllerCard from '$lib/components/endgame/FinaleControllerCard.svelte';
	import { createLocalStorageStore } from '$lib/local-storage-store.js';
	import { connectionLabel, messages, onOffLabel, pageTitle } from '$lib/i18n';
	import type { ReactionEmoji } from '$lib/reactions.js';
	import { createReconnectingWebSocket } from '$lib/reconnecting-websocket.js';
	import { onDestroy, onMount } from 'svelte';
	import { get, type Writable } from 'svelte/store';
	import { createSoundSystem } from '$lib/sound-system.js';

	const { data } = $props();
	const lobby = () => data.lobby;
	const SAFETY_RESYNC_INTERVAL_MS = 120_000;

	const player: Writable<Player | null> = createLocalStorageStore('playerData', null);
	if ($player === null) {
		goto('/play');
	}

	const controller = createControllerStore(
		{
			id: $player?.id || '',
			players: lobby().players,
			lastRevision: 0,
			isHost: lobby().host_id === $player?.id,
			gameState: lobby().state,
			lobbyPhase: lobby().phase ?? 'waiting',
			currentStep: lobby().current_step ?? 0,
			hostEnabled: lobby().host_enabled,
			starterPlayerId: lobby().starter_id,
			activeStep: undefined,
			displayPhase: 'question_active',
			scoreboardVisible: false,
			buzzerActive: false,
			buzzedPlayerId: undefined,
			disabledBuzzerPlayerIds: [],
			submittedPlayerIds: [],
			hasSubmitted: false,
			submissionCount: 0,
			pendingReviewCount: 0,
			revealedSubmission: undefined,
			revealedAnswer: undefined,
			hostAnswer: undefined,
			submissions: [],
			endGame: undefined,
			lastReaction: undefined
		},
		onKick
	);
	const soundSystem = createSoundSystem('controller');

	let isConnected = $state(false);
	let customScore = $state(0);
	let socket: ReturnType<typeof createReconnectingWebSocket> | null = null;
	let resyncPending = $state(false);
	let resyncIntervalId: number | null = null;
	let finaleAutoplayIntervalId: number | null = null;
	let reviewStepId = $state<string | undefined>(undefined);
	let pendingReviewedPlayerIds = $state<string[]>([]);

	const playerMap = $derived(new Map($controller.players.map((entry) => [entry.id, entry])));
	const basePlayerInputDisabled = $derived(
		!$controller.isHost &&
			($controller.lobbyPhase !== 'question_active' ||
				!$controller.activeStep?.input_enabled ||
				$controller.hasSubmitted)
	);
	const submittedPlayerNames = $derived(
		$controller.submittedPlayerIds
			.map((playerId) => playerMap.get(playerId)?.name ?? playerId)
			.filter(Boolean)
	);
	const gameFinished = $derived(
		$controller.lobbyPhase === 'finished' || Boolean($controller.endGame)
	);
	const canStartHostlessGame = $derived(
		!$controller.hostEnabled && $controller.starterPlayerId === $controller.id
	);
	const canContinueHostlessInfoSlide = $derived(
		canStartHostlessGame &&
			$controller.activeStep?.input_kind === 'none' &&
			$controller.activeStep?.evaluation_type === 'none' &&
			$controller.lobbyPhase === 'question_active'
	);
	const canSendReactions = $derived($controller.gameState !== 'waiting_for_players');

	$effect(() => {
		const stepId = $controller.activeStep?.id;
		if (stepId !== reviewStepId) {
			reviewStepId = stepId;
			pendingReviewedPlayerIds = [];
		}
	});

	$effect(() => {
		const reviewedIds = new Set(
			$controller.submissions
				.filter((submission) => submission.reviewed)
				.map((submission) => submission.player_id)
		);
		const remainingPending = pendingReviewedPlayerIds.filter(
			(playerId) => !reviewedIds.has(playerId)
		);
		if (remainingPending.length !== pendingReviewedPlayerIds.length) {
			pendingReviewedPlayerIds = remainingPending;
		}
	});

	$effect(() => {
		if (finaleAutoplayIntervalId !== null) {
			clearInterval(finaleAutoplayIntervalId);
			finaleAutoplayIntervalId = null;
		}
		if (
			!browser ||
			!$controller.isHost ||
			!$controller.endGame?.revealed ||
			!$controller.endGame.autoplay_enabled ||
			$controller.endGame.sequence_stage === 'scoreboard'
		) {
			return;
		}
		finaleAutoplayIntervalId = window.setInterval(() => {
			sendAction({ type_: 'advance_end_game_stage' });
		}, 4500);
		return () => {
			if (finaleAutoplayIntervalId !== null) {
				clearInterval(finaleAutoplayIntervalId);
				finaleAutoplayIntervalId = null;
			}
		};
	});

	onMount(() => {
		if (!browser || !$player?.game_id || !$player?.id) {
			return;
		}
		soundSystem.syncState(get(controller), { baseline: true });
		soundSystem.start(() => get(controller));
		const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
		socket = createReconnectingWebSocket(
			`${protocol}://${window.location.host}/api/v1/game/${$player.game_id}/controller/${$player.id}`,
			{
				onMessage: (data) => {
					const message = JSON.parse(data) as { type_: string };
					const resyncSnapshot = message.type_ === 'runtime_snapshot' && resyncPending;
					const result = controller.onMessage(data);
					soundSystem.handleEvent(message, get(controller));
					soundSystem.syncState(get(controller), { suppressCues: resyncSnapshot });
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
		return () => {
			if (resyncIntervalId !== null) {
				clearInterval(resyncIntervalId);
				resyncIntervalId = null;
			}
			if (finaleAutoplayIntervalId !== null) {
				clearInterval(finaleAutoplayIntervalId);
				finaleAutoplayIntervalId = null;
			}
			soundSystem.dispose();
			socket?.close();
			socket = null;
		};
	});

	onDestroy(() => {
		if (resyncIntervalId !== null) {
			clearInterval(resyncIntervalId);
			resyncIntervalId = null;
		}
		if (finaleAutoplayIntervalId !== null) {
			clearInterval(finaleAutoplayIntervalId);
			finaleAutoplayIntervalId = null;
		}
		soundSystem.dispose();
		socket?.close();
		socket = null;
	});

	function sendAction(msg: Record<string, unknown>) {
		socket?.send(
			JSON.stringify({
				...msg,
				player_id: $controller.id
			})
		);
	}

	function requestResync() {
		if (resyncPending) {
			return;
		}
		const sent = socket?.send(
			JSON.stringify({
				type_: 'resync_request',
				last_revision: $controller.lastRevision
			})
		);
		if (sent) {
			resyncPending = true;
		}
	}

	function sendReaction(reaction: ReactionEmoji) {
		sendAction({ type_: 'player_reaction', reaction });
	}

	function startGame() {
		sendAction({ type_: 'start_game' });
	}

	function nextStep() {
		if ($controller.displayPhase === 'answer_reveal') {
			sendAction({ type_: 'step_advanced' });
			return;
		}
		if ($controller.lobbyPhase === 'question_active') {
			sendAction({ type_: 'close_step' });
			return;
		}
		sendAction({ type_: 'show_answer_reveal' });
	}

	function previousStep() {
		if ($controller.displayPhase !== 'answer_reveal') {
			return;
		}
		sendAction({ type_: 'show_question' });
	}

	function resetStep() {
		sendAction({ type_: 'reset_step' });
	}

	function toggleScoreboardVisibility() {
		sendAction({
			type_: 'scoreboard_visibility',
			visible: !$controller.scoreboardVisible
		});
	}

	function toggleMediaPlayback() {
		if ($controller.activeStep?.media?.type_ !== 'video') {
			return;
		}
		sendAction({
			type_: 'media_playback',
			paused: !$controller.activeStep.media.paused
		});
	}

	function restartMedia() {
		if ($controller.activeStep?.media?.type_ !== 'video') {
			return;
		}
		sendAction({
			type_: 'media_playback',
			paused: false,
			restart: true
		});
	}

	function evaluateStep() {
		sendAction({ type_: 'scores_updated' });
	}

	function toggleBuzzerState() {
		sendAction({ type_: 'buzzer_state', active: !$controller.buzzerActive });
	}

	function revealEndGame() {
		sendAction({ type_: 'reveal_end_game' });
	}

	function advanceEndGameStage() {
		sendAction({ type_: 'advance_end_game_stage' });
	}

	function toggleEndGameAutoplay() {
		sendAction({
			type_: 'toggle_end_game_autoplay',
			enabled: !$controller.endGame?.autoplay_enabled
		});
	}

	function reviewSubmission(playerId: string, accepted: boolean, pointsOverride?: number) {
		if (!pendingReviewedPlayerIds.includes(playerId)) {
			pendingReviewedPlayerIds = [...pendingReviewedPlayerIds, playerId];
		}
		socket?.send(
			JSON.stringify({
				type_: 'review_submission',
				player_id: playerId,
				accepted,
				points_override: pointsOverride
			})
		);
	}

	function revealSubmission(playerId?: string) {
		socket?.send(
			JSON.stringify({
				type_: 'revealed_submission',
				player_id: playerId
			})
		);
	}

	function adjustScore(playerId: string, amount: number, useSet = false) {
		socket?.send(
			JSON.stringify({
				type_: 'update_score',
				player_id: playerId,
				add_score: useSet ? 0 : amount,
				set_score: useSet ? amount : undefined
			})
		);
	}

	function submitAnswer(value: unknown) {
		sendAction({
			type_: 'player_input_submitted',
			value
		});
	}

	function isSubmissionReviewed(playerId: string) {
		return (
			pendingReviewedPlayerIds.includes(playerId) ||
			$controller.submissions.some(
				(submission) => submission.player_id === playerId && submission.reviewed
			)
		);
	}

	function onKick() {
		try {
			const playerDataByJoinCode = JSON.parse(
				localStorage.getItem('playerDataByJoinCode') ?? '{}'
			) as Record<string, Player>;
			delete playerDataByJoinCode[lobby().join_code];
			localStorage.setItem('playerDataByJoinCode', JSON.stringify(playerDataByJoinCode));
		} catch {
			localStorage.removeItem('playerDataByJoinCode');
		}
		localStorage.removeItem('playerData');
		socket?.close();
		socket = null;
		goto('/');
	}
</script>

<svelte:head>
	<title
		>{pageTitle(
			$controller.isHost
				? $messages.gameplay.hostControllerTitle
				: $messages.gameplay.playerControllerTitle
		)}</title
	>
</svelte:head>

<GameConnectionStatus
	connected={isConnected}
	connectionLabel={connectionLabel(isConnected)}
	showInline={false}
	showDisconnectedChip={true}
/>

{#if $controller.scoreboardVisible && !$controller.endGame?.revealed && !$controller.isHost}
	<p class="mt-3 text-center text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
		{$messages.gameplay.scoreboardShowingOnMainScreen}
	</p>
{/if}

{#if $controller.gameState === 'waiting_for_players'}
	<div class="card mt-0 text-center">
		<p class="text-xl font-bold">{$messages.gameplay.waitingForGameStart}</p>
		{#if $controller.isHost}
			<p class="mt-2 text-lg">{$messages.gameplay.youAreHostController}</p>
			<button type="button" class="btn btn-primary mt-4 text-3xl" onclick={startGame}
				>{$messages.gameplay.startGame}</button
			>
		{:else if canStartHostlessGame}
			<p class="mt-2 text-lg">{$messages.gameplay.youCanStartAsFirstPlayer}</p>
			<button type="button" class="btn btn-primary mt-4 text-3xl" onclick={startGame}
				>{$messages.gameplay.startGame}</button
			>
		{/if}
	</div>
{:else}
	<div class="mt-0 stack-lg">
		{#if $controller.endGame?.revealed}
			<FinaleControllerCard endGame={$controller.endGame} playerId={$controller.id} />

			{#if $controller.isHost}
				<section class="card stack-md">
					<h2 class="label-title text-2xl">{$messages.gameplay.finaleControls}</h2>
					<p class="text-sm text-slate-600">
						{$messages.gameplay.stage}: {$messages.finale.stageLabel(
							$controller.endGame.sequence_stage
						)} · {$messages.gameplay.autoplay}:
						{onOffLabel($controller.endGame.autoplay_enabled)}
					</p>
					<div class="flex flex-wrap gap-3">
						<button type="button" class="btn btn-ghost" onclick={revealEndGame}>
							{$messages.gameplay.resetToPodium}
						</button>
						<button
							type="button"
							class="btn btn-primary"
							onclick={advanceEndGameStage}
							disabled={$controller.endGame.sequence_stage === 'scoreboard'}
						>
							{$messages.gameplay.nextFinaleStage}
						</button>
						<button type="button" class="btn btn-ghost" onclick={toggleEndGameAutoplay}>
							{$controller.endGame.autoplay_enabled
								? $messages.gameplay.disableAutoplay
								: $messages.gameplay.enableAutoplay}
						</button>
					</div>
				</section>
			{/if}
		{:else if !gameFinished && !$controller.isHost}
			<PlayerInputPanel
				activeStep={$controller.activeStep}
				baseInputDisabled={basePlayerInputDisabled}
				buzzerActive={$controller.buzzerActive}
				{canContinueHostlessInfoSlide}
				disabledBuzzerPlayerIds={$controller.disabledBuzzerPlayerIds}
				hasSubmitted={$controller.hasSubmitted}
				playerId={$controller.id}
				onContinueInfoSlide={nextStep}
				onSubmitAnswer={submitAnswer}
			/>
		{:else if gameFinished}
			<section class="card text-center">
				<p class="text-xl font-bold">{$messages.gameplay.gameComplete}</p>
				<p class="mt-2 text-slate-600">
					{$controller.isHost
						? $messages.gameplay.revealFinaleFromHost
						: $messages.gameplay.waitingForFinalResults}
				</p>
			</section>
		{/if}

		{#if canSendReactions && !$controller.isHost}
			<ReactionBar connected={isConnected} onReact={sendReaction} />
		{/if}

		{#if $controller.isHost && !$controller.endGame?.revealed && gameFinished}
			<section class="card stack-md">
				<h2 class="label-title text-2xl">{$messages.gameplay.finaleControls}</h2>
				<p class="text-sm text-slate-600">{$messages.gameplay.gameFinishedRevealEndScreen}</p>
				<div class="flex flex-wrap gap-3">
					<button type="button" class="btn btn-primary" onclick={revealEndGame}
						>{$messages.gameplay.revealFinale}</button
					>
					<button type="button" class="btn btn-ghost" onclick={toggleEndGameAutoplay}>
						{$controller.endGame?.autoplay_enabled
							? $messages.gameplay.disableAutoplay
							: $messages.gameplay.enableAutoplay}
					</button>
				</div>
			</section>
		{/if}

		{#if $controller.isHost && !gameFinished && !$controller.endGame?.revealed}
			<HostControlsPanel
				activeStep={$controller.activeStep}
				buzzerActive={$controller.buzzerActive}
				displayPhase={$controller.displayPhase}
				hostEnabled={$controller.hostEnabled}
				lobbyPhase={$controller.lobbyPhase}
				pendingReviewCount={$controller.pendingReviewCount}
				scoreboardVisible={$controller.scoreboardVisible}
				submissionCount={$controller.submissionCount}
				{submittedPlayerNames}
				onEvaluateStep={evaluateStep}
				onNextStep={nextStep}
				onPreviousStep={previousStep}
				onResetStep={resetStep}
				onRestartMedia={restartMedia}
				onToggleBuzzer={toggleBuzzerState}
				onToggleMediaPlayback={toggleMediaPlayback}
				onToggleScoreboardVisibility={toggleScoreboardVisibility}
			/>

			<HostReviewQueue
				activeStep={$controller.activeStep}
				buzzedPlayerId={$controller.buzzedPlayerId}
				{customScore}
				disabledBuzzerPlayerIds={$controller.disabledBuzzerPlayerIds}
				hostAnswer={$controller.hostAnswer}
				{playerMap}
				submissions={$controller.submissions}
				{isSubmissionReviewed}
				onRevealSubmission={revealSubmission}
				onReviewSubmission={reviewSubmission}
			/>

			<section class="card stack-md">
				<h2 class="label-title text-2xl">{$messages.gameplay.manualScore}</h2>
				<input class="input" type="number" bind:value={customScore} min="-500" max="500" />
				<div class="flex flex-wrap gap-2">
					{#each $controller.players.filter((entry) => entry.id !== $controller.id) as entry}
						<button
							type="button"
							class="btn btn-ghost"
							onclick={() => adjustScore(entry.id, customScore)}
						>
							{entry.name}
						</button>
					{/each}
				</div>
			</section>
		{/if}
	</div>
{/if}
