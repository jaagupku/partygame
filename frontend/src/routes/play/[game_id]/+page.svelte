<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { createControllerStore } from '$lib/controller-store.js';
	import { createLocalStorageStore } from '$lib/local-storage-store.js';
	import { createReconnectingWebSocket } from '$lib/reconnecting-websocket.js';
	import { onDestroy, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';

	const { data } = $props();
	const lobby = () => data.lobby;

	const player: Writable<Player | null> = createLocalStorageStore('playerData', null);
	if ($player === null) {
		goto('/play');
	}

	const controller = createControllerStore(
		{
			id: $player?.id || '',
			isHost: lobby().host_id === $player?.id,
			gameState: lobby().state,
			lobbyPhase: lobby().phase ?? 'waiting',
			currentStep: lobby().current_step ?? 0,
			hostEnabled: lobby().host_enabled,
			activeStep: undefined,
			buzzerActive: false,
			buzzedPlayerId: undefined,
			submissionCount: 0,
			pendingReviewCount: 0,
			revealedSubmission: undefined,
			submissions: []
		},
		onKick
	);

	let isConnected = $state(false);
	let answerValue = $state<string | number>('');
	let orderingItems = $state<string[]>([]);
	let customScore = $state(0);
	let orderingStepId = $state<string | undefined>(undefined);
	let socket: ReturnType<typeof createReconnectingWebSocket> | null = null;

	const playerMap = $derived(new Map(lobby().players.map((entry) => [entry.id, entry])));

	$effect(() => {
		const step = $controller.activeStep;
		if (step?.input_kind !== 'ordering') {
			orderingItems = [];
			orderingStepId = undefined;
			return;
		}
		if (orderingStepId === step.id) {
			return;
		}
		orderingStepId = step.id;
		orderingItems = [...step.input_options];
	});

	onMount(() => {
		if (!browser || !$player?.game_id || !$player?.id) {
			return;
		}
		const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
		socket = createReconnectingWebSocket(
			`${protocol}://${window.location.host}/api/v1/game/${$player.game_id}/controller/${$player.id}`,
			{
				onMessage: (data) => controller.onMessage(data),
				onStatusChange: (connected) => {
					isConnected = connected;
				}
			}
		);
		return () => {
			socket?.close();
			socket = null;
		};
	});

	onDestroy(() => {
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

	function startGame() {
		sendAction({ type_: 'start_game' });
	}

	function nextStep() {
		sendAction({ type_: 'step_advanced' });
	}

	function evaluateStep() {
		sendAction({ type_: 'scores_updated' });
	}

	function closeStep() {
		sendAction({ type_: 'close_step' });
	}

	function reviewSubmission(playerId: string, accepted: boolean, pointsOverride?: number) {
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
		if (!step) {
			return;
		}
		let value: unknown = answerValue;
		if (step.input_kind === 'number') {
			value = Number(answerValue);
		} else if (step.input_kind === 'ordering') {
			value = orderingItems;
		} else if (step.input_kind === 'text') {
			value = String(answerValue);
		}

		sendAction({
			type_: 'player_input_submitted',
			value
		});
	}

	function buzz() {
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

	function moveOrderingItem(index: number, direction: -1 | 1) {
		const nextIndex = index + direction;
		if (nextIndex < 0 || nextIndex >= orderingItems.length) {
			return;
		}
		const next = [...orderingItems];
		[next[index], next[nextIndex]] = [next[nextIndex], next[index]];
		orderingItems = next;
	}
</script>

<h1 class="page-title">Party Controller</h1>
<p class="page-subtitle">Connection: {isConnected ? 'Live' : 'Connecting...'}</p>

{#if $controller.gameState === 'waiting_for_players'}
	<div class="card mt-8 text-center">
		<p class="text-xl font-bold">Waiting for game to start.</p>
		{#if $controller.isHost}
			<p class="mt-2 text-lg">You are the host controller.</p>
			<button type="button" class="btn btn-primary mt-4 text-3xl" onclick={startGame}
				>Start Game</button
			>
		{/if}
	</div>
{:else}
	<div class="mt-8 stack-lg">
		{#if !$controller.isHost && $controller.activeStep?.input_kind === 'buzzer'}
			<section class="card stack-md text-center">
				<h2 class="label-title text-2xl">Buzzer</h2>
				<p>{$controller.buzzerActive ? 'Buzz now!' : 'Wait for the host to continue.'}</p>
				<button
					type="button"
					disabled={!$controller.buzzerActive}
					class="btn btn-accent text-4xl"
					onclick={buzz}
				>
					BUZZ
				</button>
			</section>
		{:else if !$controller.isHost && $controller.activeStep?.input_kind === 'text'}
			<section class="card stack-md">
				<h2 class="label-title text-2xl">Your Answer</h2>
				<input
					class="input"
					type="text"
					bind:value={answerValue}
					placeholder={$controller.activeStep?.input_placeholder ?? 'Type your answer'}
				/>
				<button type="button" class="btn btn-primary" onclick={submitAnswer}>Submit Answer</button>
			</section>
		{:else if !$controller.isHost && $controller.activeStep?.input_kind === 'number'}
			<section class="card stack-md">
				<h2 class="label-title text-2xl">Your Answer</h2>
				<input
					class="input"
					type="number"
					min={$controller.activeStep?.slider_min}
					max={$controller.activeStep?.slider_max}
					step={$controller.activeStep?.slider_step ?? 1}
					bind:value={answerValue}
					placeholder={$controller.activeStep?.input_placeholder ?? 'Enter a number'}
				/>
				<button type="button" class="btn btn-primary" onclick={submitAnswer}>Submit Answer</button>
			</section>
		{:else if !$controller.isHost && $controller.activeStep?.input_kind === 'ordering'}
			<section class="card stack-md">
				<h2 class="label-title text-2xl">Ordering Answer</h2>
				<p class="text-sm text-slate-600">Move the items until they are in the correct order.</p>
				<div class="stack-md">
					{#each orderingItems as item, index (item)}
						<div class="flex items-center gap-3 rounded-2xl bg-white/70 p-3">
							<div class="badge bg-slate-100 text-slate-700">#{index + 1}</div>
							<div class="flex-1 font-semibold">{item}</div>
							<div class="flex gap-2">
								<button
									type="button"
									class="btn btn-ghost px-3 py-2 text-sm"
									disabled={index === 0}
									onclick={() => moveOrderingItem(index, -1)}
								>
									Up
								</button>
								<button
									type="button"
									class="btn btn-ghost px-3 py-2 text-sm"
									disabled={index === orderingItems.length - 1}
									onclick={() => moveOrderingItem(index, 1)}
								>
									Down
								</button>
							</div>
						</div>
					{/each}
				</div>
				<button type="button" class="btn btn-primary" onclick={submitAnswer}>Submit Order</button>
			</section>
		{:else if !$controller.isHost}
			<section class="card text-center">
				<p class="text-lg">No phone input is required for this step.</p>
			</section>
		{/if}

		{#if $controller.isHost}
			<section class="card stack-md">
				<h2 class="label-title text-2xl">Host Controls</h2>
				<p class="text-sm text-slate-600">
					Phase: {$controller.lobbyPhase} · Submissions: {$controller.submissionCount} · Pending review:
					{$controller.pendingReviewCount}
				</p>
				<div class="flex flex-wrap gap-3">
					{#if $controller.lobbyPhase === 'question_active'}
						<button type="button" class="btn btn-primary" onclick={closeStep}>Close Step</button>
					{:else if !$controller.hostEnabled || $controller.activeStep?.evaluation_type !== 'host_judged'}
						<button type="button" class="btn btn-primary" onclick={evaluateStep}
							>Auto Evaluate</button
						>
					{/if}
					<button type="button" class="btn btn-accent" onclick={nextStep}>Next Step</button>
					{#if $controller.activeStep?.input_kind === 'buzzer'}
						<button
							type="button"
							class="btn btn-ghost"
							onclick={() =>
								socket?.send(
									JSON.stringify({ type_: 'buzzer_state', active: !$controller.buzzerActive })
								)}
						>
							{$controller.buzzerActive ? 'Disable Buzzer' : 'Enable Buzzer'}
						</button>
					{/if}
				</div>
			</section>

			<section class="card stack-md">
				<h2 class="label-title text-2xl">Review Queue</h2>
				{#if $controller.activeStep?.input_kind === 'buzzer' && $controller.buzzedPlayerId}
					<div class="rounded-2xl bg-white/70 p-3">
						<p class="font-bold">{playerMap.get($controller.buzzedPlayerId)?.name}</p>
						<p class="mt-1 text-slate-600">Buzzed in first</p>
						<div class="mt-3 flex flex-wrap gap-2">
							<button
								type="button"
								class="btn btn-primary"
								onclick={() =>
									reviewSubmission(
										$controller.buzzedPlayerId ?? '',
										true,
										$controller.activeStep?.evaluation_points
									)}
							>
								Accept +{$controller.activeStep?.evaluation_points ?? 1}
							</button>
							<button
								type="button"
								class="btn btn-danger"
								onclick={() => reviewSubmission($controller.buzzedPlayerId ?? '', false)}
							>
								Reject
							</button>
						</div>
					</div>
				{:else if $controller.submissions.length === 0}
					<p class="text-slate-500">No answers submitted yet.</p>
				{:else}
					{#each $controller.submissions as submission}
						<div
							class={`rounded-2xl p-3 ${submission.reviewed ? 'bg-slate-100 opacity-70' : 'bg-white/70'}`}
						>
							<p class="font-bold">{playerMap.get(submission.player_id)?.name}</p>
							<p class="mt-1 break-words">{String(submission.value)}</p>
							<div class="mt-3 flex flex-wrap gap-2">
								<button
									type="button"
									class="btn btn-ghost"
									onclick={() => revealSubmission(submission.player_id)}
								>
									Reveal
								</button>
								{#if !submission.reviewed}
									<button
										type="button"
										class="btn btn-primary"
										onclick={() =>
											reviewSubmission(
												submission.player_id,
												true,
												$controller.activeStep?.evaluation_points
											)}
									>
										Accept +{$controller.activeStep?.evaluation_points ?? 1}
									</button>
									<button
										type="button"
										class="btn btn-danger"
										onclick={() => reviewSubmission(submission.player_id, false)}
									>
										Reject
									</button>
									{#if customScore !== 0}
										<button
											type="button"
											class="btn btn-ghost"
											onclick={() => reviewSubmission(submission.player_id, true, customScore)}
										>
											Accept {customScore > 0 ? '+' : ''}{customScore}
										</button>
									{/if}
								{:else}
									<span class="badge bg-slate-200 text-slate-700">Reviewed</span>
								{/if}
							</div>
						</div>
					{/each}
				{/if}
			</section>

			<section class="card stack-md">
				<h2 class="label-title text-2xl">Manual Score</h2>
				<input class="input" type="number" bind:value={customScore} min="-500" max="500" />
				<div class="flex flex-wrap gap-2">
					{#each lobby().players.filter((entry) => entry.id !== $controller.id) as entry}
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
