<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { createControllerStore } from '$lib/controller-store.js';
	import HostControlsPanel from '$lib/components/controller/HostControlsPanel.svelte';
	import HostReviewQueue from '$lib/components/controller/HostReviewQueue.svelte';
	import GameConnectionStatus from '$lib/components/GameConnectionStatus.svelte';
	import ReactionBar from '$lib/components/controller/ReactionBar.svelte';
	import FinaleControllerCard from '$lib/components/endgame/FinaleControllerCard.svelte';
	import { triggerBuzzerHapticPulse } from '$lib/haptics.js';
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
	let answerValue = $state<string | number>('');
	let orderingItems = $state<string[]>([]);
	let selectedRadioOption = $state<string | null>(null);
	let selectedCheckboxOptions = $state<string[]>([]);
	let customScore = $state(0);
	let orderingStepId = $state<string | undefined>(undefined);
	let inputStepId = $state<string | undefined>(undefined);
	let draggedOrderingIndex = $state<number | null>(null);
	let dropOrderingIndex = $state<number | null>(null);
	let socket: ReturnType<typeof createReconnectingWebSocket> | null = null;
	let resyncPending = $state(false);
	let resyncIntervalId: number | null = null;
	let finaleAutoplayIntervalId: number | null = null;
	let pendingSubmissionStepId = $state<string | undefined>(undefined);
	let pendingReviewedPlayerIds = $state<string[]>([]);

	const playerMap = $derived(new Map($controller.players.map((entry) => [entry.id, entry])));
	const playerInputDisabled = $derived(
		!$controller.isHost &&
			($controller.lobbyPhase !== 'question_active' ||
				!$controller.activeStep?.input_enabled ||
				$controller.hasSubmitted ||
				pendingSubmissionStepId === $controller.activeStep?.id)
	);
	const buzzerLockedOut = $derived($controller.disabledBuzzerPlayerIds.includes($controller.id));
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
		const step = $controller.activeStep;
		if (step?.id !== inputStepId) {
			answerValue = '';
			selectedRadioOption = null;
			selectedCheckboxOptions = [];
			inputStepId = step?.id;
			pendingSubmissionStepId = undefined;
			pendingReviewedPlayerIds = [];
		}
		if (step?.input_kind !== 'ordering') {
			orderingItems = [];
			orderingStepId = undefined;
			draggedOrderingIndex = null;
			dropOrderingIndex = null;
			return;
		}
		if (orderingStepId === step.id) {
			return;
		}
		orderingStepId = step.id;
		orderingItems = [...step.input_options];
		draggedOrderingIndex = null;
		dropOrderingIndex = null;
	});

	$effect(() => {
		if ($controller.hasSubmitted) {
			pendingSubmissionStepId = undefined;
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

	function submitAnswer() {
		const step = $controller.activeStep;
		if (!step || playerInputDisabled) {
			return;
		}
		let value: unknown = answerValue;
		if (step.input_kind === 'number') {
			value = Number(answerValue);
		} else if (step.input_kind === 'ordering') {
			value = orderingItems;
		} else if (step.input_kind === 'radio') {
			value = selectedRadioOption;
		} else if (step.input_kind === 'checkbox') {
			value = selectedCheckboxOptions;
		} else if (step.input_kind === 'text') {
			value = String(answerValue);
		}

		pendingSubmissionStepId = step.id;
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

	function buzz() {
		if (playerInputDisabled || buzzerLockedOut || !$controller.buzzerActive) {
			return;
		}
		triggerBuzzerHapticPulse();
		pendingSubmissionStepId = $controller.activeStep?.id;
		sendAction({
			type_: 'player_input_submitted',
			value: 'buzz'
		});
	}

	function onKick() {
		localStorage.removeItem('playerData');
		socket?.close();
		socket = null;
		goto('/');
	}

	function reorderOrderingItems(fromIndex: number, toIndex: number) {
		if (
			fromIndex === toIndex ||
			fromIndex < 0 ||
			toIndex < 0 ||
			fromIndex >= orderingItems.length ||
			toIndex >= orderingItems.length
		) {
			return;
		}
		const next = [...orderingItems];
		const [movedItem] = next.splice(fromIndex, 1);
		next.splice(toIndex, 0, movedItem);
		orderingItems = next;
	}

	function startOrderingDrag(index: number) {
		if (playerInputDisabled) {
			return;
		}
		draggedOrderingIndex = index;
		dropOrderingIndex = index;
	}

	function updateOrderingDropTarget(index: number) {
		if (playerInputDisabled || draggedOrderingIndex === null) {
			return;
		}
		dropOrderingIndex = index;
	}

	function finishOrderingDrop(index: number) {
		if (playerInputDisabled || draggedOrderingIndex === null) {
			draggedOrderingIndex = null;
			dropOrderingIndex = null;
			return;
		}
		reorderOrderingItems(draggedOrderingIndex, index);
		draggedOrderingIndex = null;
		dropOrderingIndex = null;
	}

	function cancelOrderingDrag() {
		draggedOrderingIndex = null;
		dropOrderingIndex = null;
	}

	function submitRadioOption(option: string) {
		selectedRadioOption = option;
		answerValue = option;
		submitAnswer();
	}

	function toggleCheckboxOption(option: string) {
		if (selectedCheckboxOptions.includes(option)) {
			selectedCheckboxOptions = selectedCheckboxOptions.filter((entry) => entry !== option);
			return;
		}
		selectedCheckboxOptions = [...selectedCheckboxOptions, option];
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
		{:else if !gameFinished && !$controller.isHost && $controller.activeStep?.input_kind === 'buzzer'}
			<section class="card stack-md text-center">
				<h2 class="label-title text-2xl">{$messages.gameplay.buzzer}</h2>
				<p>
					{playerInputDisabled
						? $controller.hasSubmitted
							? $messages.gameplay.answerReceivedWaiting
							: $messages.gameplay.stepClosed
						: buzzerLockedOut
							? $messages.gameplay.buzzerChanceUsed
							: $controller.buzzerActive
								? $messages.gameplay.buzzNow
								: $messages.gameplay.waitForHost}
				</p>
				<button
					type="button"
					disabled={playerInputDisabled || !$controller.buzzerActive || buzzerLockedOut}
					class="btn btn-accent text-4xl"
					onclick={buzz}
				>
					{$messages.gameplay.buzzer}
				</button>
			</section>
		{:else if !gameFinished && !$controller.isHost && $controller.activeStep?.input_kind === 'text'}
			<section class="card stack-md">
				<h2 class="label-title text-2xl">{$messages.gameplay.yourAnswer}</h2>
				{#if playerInputDisabled}
					<p class="text-sm text-slate-600">
						{$controller.hasSubmitted
							? $messages.gameplay.answerSubmitted
							: $messages.gameplay.stepClosedAnswersDisabled}
					</p>
				{/if}
				<input
					class="input"
					type="text"
					bind:value={answerValue}
					disabled={playerInputDisabled}
					placeholder={$controller.activeStep?.input_placeholder ??
						$messages.gameplay.typeYourAnswer}
				/>
				<button
					type="button"
					class="btn btn-primary"
					onclick={submitAnswer}
					disabled={playerInputDisabled}
				>
					{$messages.gameplay.submitAnswer}
				</button>
			</section>
		{:else if !gameFinished && !$controller.isHost && $controller.activeStep?.input_kind === 'number'}
			<section class="card stack-md">
				<h2 class="label-title text-2xl">{$messages.gameplay.yourAnswer}</h2>
				{#if playerInputDisabled}
					<p class="text-sm text-slate-600">
						{$controller.hasSubmitted
							? $messages.gameplay.answerSubmitted
							: $messages.gameplay.stepClosedAnswersDisabled}
					</p>
				{/if}
				<input
					class="input"
					type="number"
					min={$controller.activeStep?.slider_min}
					max={$controller.activeStep?.slider_max}
					step={$controller.activeStep?.slider_step ?? 1}
					bind:value={answerValue}
					disabled={playerInputDisabled}
					placeholder={$controller.activeStep?.input_placeholder ?? $messages.gameplay.enterNumber}
				/>
				<button
					type="button"
					class="btn btn-primary"
					onclick={submitAnswer}
					disabled={playerInputDisabled}
				>
					{$messages.gameplay.submitAnswer}
				</button>
			</section>
		{:else if !gameFinished && !$controller.isHost && $controller.activeStep?.input_kind === 'ordering'}
			<section class="card stack-md">
				<h2 class="label-title text-2xl">{$messages.gameplay.orderingAnswer}</h2>
				<p class="text-sm text-slate-600">
					{playerInputDisabled
						? $controller.hasSubmitted
							? $messages.gameplay.orderSubmitted
							: $messages.gameplay.reorderingDisabled
						: $messages.gameplay.dragItemsToOrder}
				</p>
				<div class="stack-md">
					{#each orderingItems as item, index}
						<div
							class={`flex items-center gap-3 rounded-2xl border p-3 transition ${
								draggedOrderingIndex === index
									? 'border-sky-300 bg-sky-50 opacity-80'
									: dropOrderingIndex === index
										? 'border-sky-200 bg-sky-50/70'
										: 'border-white/70 bg-white/70'
							}`}
							role="listitem"
							aria-grabbed={draggedOrderingIndex === index}
							draggable={!playerInputDisabled}
							ondragstart={() => startOrderingDrag(index)}
							ondragover={(event) => {
								event.preventDefault();
								updateOrderingDropTarget(index);
							}}
							ondrop={(event) => {
								event.preventDefault();
								finishOrderingDrop(index);
							}}
							ondragend={cancelOrderingDrag}
						>
							<div class="badge bg-slate-100 text-slate-700">#{index + 1}</div>
							<div
								class="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-500"
								aria-hidden="true"
							>
								::
							</div>
							<div class="flex-1 font-semibold">{item}</div>
						</div>
					{/each}
				</div>
				<button
					type="button"
					class="btn btn-primary"
					onclick={submitAnswer}
					disabled={playerInputDisabled}
				>
					{$messages.gameplay.submitOrder}
				</button>
			</section>
		{:else if !gameFinished && !$controller.isHost && $controller.activeStep?.input_kind === 'radio'}
			<section class="card stack-md">
				<h2 class="label-title text-2xl">{$messages.gameplay.chooseOne}</h2>
				<p class="text-sm text-slate-600">
					{playerInputDisabled
						? $controller.hasSubmitted
							? $messages.gameplay.choiceLocked
							: $messages.gameplay.newSelectionsDisabled
						: $messages.gameplay.tapOneOption}
				</p>
				<div class="grid gap-3">
					{#each $controller.activeStep.input_options as option}
						<button
							type="button"
							class="btn btn-ghost justify-start text-left text-xl"
							disabled={playerInputDisabled}
							onclick={() => submitRadioOption(option)}
						>
							{option}
						</button>
					{/each}
				</div>
			</section>
		{:else if !gameFinished && !$controller.isHost && $controller.activeStep?.input_kind === 'checkbox'}
			<section class="card stack-md">
				<h2 class="label-title text-2xl">{$messages.gameplay.chooseOneOrMore}</h2>
				<p class="text-sm text-slate-600">
					{playerInputDisabled
						? $controller.hasSubmitted
							? $messages.gameplay.selectionSubmitted
							: $messages.gameplay.newSelectionsDisabled
						: $messages.gameplay.tapOptionsThenSubmit}
				</p>
				<div class="grid gap-3">
					{#each $controller.activeStep.input_options as option}
						<button
							type="button"
							class={`btn justify-start text-left text-xl ${
								selectedCheckboxOptions.includes(option) ? 'btn-primary text-white' : 'btn-ghost'
							}`}
							disabled={playerInputDisabled}
							onclick={() => toggleCheckboxOption(option)}
						>
							{option}
						</button>
					{/each}
				</div>
				<button
					type="button"
					class="btn btn-primary"
					onclick={submitAnswer}
					disabled={playerInputDisabled || selectedCheckboxOptions.length === 0}
				>
					{$messages.gameplay.submitSelection}
				</button>
			</section>
		{:else if !gameFinished && !$controller.isHost}
			<section class="card text-center">
				<p class="text-lg">{$messages.gameplay.noPhoneInput}</p>
				{#if canContinueHostlessInfoSlide}
					<p class="mt-2 text-slate-600">{$messages.gameplay.youCanContinueInfoSlide}</p>
					<button type="button" class="btn btn-primary mt-4" onclick={nextStep}>
						{$messages.gameplay.advanceStep}
					</button>
				{/if}
			</section>
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
