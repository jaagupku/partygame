<script lang="ts">
	import { onMount } from 'svelte';
	import DrawingInput from '$lib/components/DrawingInput.svelte';
	import DrawingDisplay from '$lib/components/DrawingDisplay.svelte';
	import DrawingCountdown from './DrawingCountdown.svelte';
	import DrawingStage from './DrawingStage.svelte';
	import { drawingText } from './helpers';
	import { messages } from '$lib/i18n';
	import { getDrawingLimitUsage } from '$lib/drawing-limits';
	let {
		view,
		ack,
		runId,
		playerId,
		organizer,
		connected,
		send
	}: {
		view: DrawingGameView;
		ack?: DrawingAck;
		runId: string;
		playerId: string;
		organizer: boolean;
		connected: boolean;
		send: (command: Record<string, unknown>) => void;
	} = $props();
	type DraftValue = { topic: string; criterion: string } | MashupBallot | DrawingSubmission | null;
	type Draft = { value: DraftValue; revision: number; dirty: boolean; inFlightValue?: DraftValue };
	type Pending = {
		id: string;
		key: string | null;
		value?: DraftValue;
		payload: Record<string, unknown>;
		sent: number;
	};
	let drafts = $state<Record<string, Draft>>({});
	let phaseKey = $state('');
	let selected = $state(0);
	let canvasVersion = $state(0);
	let pending = $state<Pending | null>(null);
	let readyRequested = $state(false);
	let error = $state('');
	let seenAck = '';
	let confirmAdvance = $state(false);
	const controlsId = $props.id();
	const cannotVote = $derived(
		view.phase === 'voting' && !!view.matchup?.drawings.some((art) => art.own)
	);
	const ready = $derived(view.ready_ids.includes(playerId));
	const disabled = $derived(view.paused || ready);
	const active = $derived(view.assignments[selected]);
	const dirty = $derived(Object.values(drafts).some((d) => d.dirty));
	const prompt = $derived(
		(drafts.prompt?.value as { topic: string; criterion: string } | undefined) ?? {
			topic: '',
			criterion: ''
		}
	);
	const ballot = $derived(
		(drafts.ballot?.value as MashupBallot | undefined) ?? {
			drawing_id: null,
			topic: false,
			criterion: false
		}
	);
	const canFinish = $derived(
		view.phase === 'writing'
			? !!prompt.topic.trim() && !!prompt.criterion.trim()
			: view.phase === 'drawing'
				? view.assignments.every((a) => drafts[a.id]?.value)
				: true
	);

	function serverDrafts(current: DrawingGameView): Record<string, Draft> {
		if (current.phase === 'writing')
			return {
				prompt: {
					value: { topic: current.prompt?.topic ?? '', criterion: current.prompt?.criterion ?? '' },
					revision: current.prompt?.revision ?? 0,
					dirty: false
				}
			};
		if (current.phase === 'drawing')
			return Object.fromEntries(
				current.assignments.map((a) => [
					a.id,
					{ value: a.value, revision: a.revision, dirty: false }
				])
			);
		if (current.phase === 'voting')
			return {
				ballot: {
					value: current.ballot ?? { drawing_id: null, topic: false, criterion: false },
					revision: 0,
					dirty: false
				}
			};
		return {};
	}
	function persist() {
		try {
			localStorage.setItem(phaseKey, JSON.stringify(drafts));
		} catch {
			/* Backend autosave still works when device storage is full. */
		}
	}
	$effect(() => {
		const nextKey = `drawing-mashup:${runId}:${playerId}:${view.phase_id}`;
		if (nextKey === phaseKey) return;
		if (phaseKey) {
			try {
				localStorage.removeItem(phaseKey);
			} catch {
				/* Storage may be unavailable. */
			}
		}
		let next = serverDrafts(view);
		try {
			const saved = JSON.parse(localStorage.getItem(nextKey) ?? '{}') as Record<string, Draft>;
			for (const [key, draft] of Object.entries(next)) {
				const local = saved[key];
				if (local?.dirty && local.revision === draft.revision) next[key] = local;
				else if (
					local?.dirty &&
					local.revision + 1 === draft.revision &&
					JSON.stringify(local.inFlightValue) === JSON.stringify(draft.value)
				) {
					next[key] = {
						...local,
						revision: draft.revision,
						dirty: JSON.stringify(local.value) !== JSON.stringify(draft.value)
					};
				}
			}
		} catch {
			/* Restore the server copy if local data is unavailable or malformed. */
		}
		drafts = next;
		phaseKey = nextKey;
		pending = null;
		readyRequested = false;
		selected = 0;
		error = '';
		confirmAdvance = false;
	});
	$effect(() => {
		if (!ack || ack.request_id === seenAck || ack.run_id !== runId) return;
		seenAck = ack.request_id;
		if (ack.request_id !== pending?.id) return;
		if (ack.status === 'ok') {
			if (pending.key && drafts[pending.key]) {
				const current = drafts[pending.key];
				drafts[pending.key] = {
					...current,
					revision: ack.revision ?? current.revision,
					dirty: JSON.stringify(current.value) !== JSON.stringify(pending.value)
				};
			}
			error = '';
		} else {
			error = ack.reason ?? 'error';
			readyRequested = false;
			if (ack.reason === 'closed' && ack.view?.paused && ack.view.phase_id === view.phase_id) {
				// Keep the local draft: a pause closes input only until the organizer resumes.
			} else if (
				ack.view &&
				(ack.reason === 'conflict' || ack.reason === 'closed' || ack.reason === 'stale')
			) {
				drafts = serverDrafts(ack.view);
				canvasVersion += 1;
			} else if (pending.key && drafts[pending.key]) drafts[pending.key].dirty = false;
		}
		pending = null;
		persist();
	});
	function update(key: string, value: DraftValue) {
		if (view.paused) return;
		if (key !== 'ballot' && ready) return;
		if (
			key !== 'prompt' &&
			key !== 'ballot' &&
			value &&
			getDrawingLimitUsage(value as DrawingSubmission).overLimit
		) {
			error = 'invalid_drawing';
			return;
		}
		drafts[key] = { ...drafts[key], value, revision: drafts[key]?.revision ?? 0, dirty: true };
		error = '';
		persist();
	}
	function command(action: string, extra: Record<string, unknown> = {}, key: string | null = null) {
		if (!connected || pending) return;
		const id = crypto.randomUUID();
		const payload = {
			type_: 'drawing_command',
			action,
			request_id: id,
			run_id: runId,
			phase_id: view.phase_id,
			...extra
		};
		pending = {
			id,
			key,
			value: key ? structuredClone($state.snapshot(drafts[key].value)) : undefined,
			payload,
			sent: Date.now()
		};
		if (key) {
			drafts[key].inFlightValue = pending.value;
			persist();
		}
		send(payload);
	}
	function flush() {
		if (!connected) return;
		if (pending) {
			if (Date.now() - pending.sent > 3000) {
				pending.sent = Date.now();
				send(pending.payload);
			}
			return;
		}
		if (view.paused || cannotVote) return;
		const entry = Object.entries(drafts).find(([, draft]) => draft.dirty);
		if (entry) {
			const [key, draft] = entry;
			if (key === 'prompt')
				command('prompt', { ...(draft.value as object), revision: draft.revision }, key);
			else if (key === 'ballot')
				command('ballot', { ballot: draft.value, matchup_id: view.matchup?.id }, key);
			else
				command('draw', { assignment_id: key, value: draft.value, revision: draft.revision }, key);
		} else if (readyRequested) {
			readyRequested = false;
			command('ready');
		}
	}
	onMount(() => {
		const timer = setInterval(flush, 400);
		return () => clearInterval(timer);
	});
	function finish() {
		readyRequested = true;
		flush();
	}
	function control(action: string) {
		if (action === 'advance' && !confirmAdvance) {
			confirmAdvance = true;
			return;
		}
		command(action);
		confirmAdvance = false;
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

<section class="card stack-md" data-drawing-phase={view.phase_id}>
	{#if view.phase === 'results'}<DrawingStage {view} />
	{:else if cannotVote}
		<p role="status">{$messages.drawingMashup.cannotVote}</p>
	{:else}
		<div class="flex flex-wrap justify-between gap-2">
			<strong>{$messages.drawingMashup[view.phase as 'writing' | 'drawing' | 'voting']}</strong
			><span
				>{view.paused
					? $messages.drawingMashup.paused
					: `${$messages.drawingMashup.progress}: ${view.ready_ids.length}/${view.participant_ids.length}`}</span
			>
		</div>
		<DrawingCountdown {view} />
		{#if view.phase === 'writing'}
			<label class="stack-sm"
				>{$messages.drawingMashup.topic}<textarea
					class="input"
					maxlength="160"
					value={prompt.topic}
					{disabled}
					oninput={(e) => update('prompt', { ...prompt, topic: e.currentTarget.value })}
				></textarea></label
			>
			<p class="theme-text-muted">{$messages.drawingMashup.topicHelp}</p>
			<label class="stack-sm"
				>{$messages.drawingMashup.criterion}<textarea
					class="input"
					maxlength="240"
					value={prompt.criterion}
					{disabled}
					oninput={(e) => update('prompt', { ...prompt, criterion: e.currentTarget.value })}
				></textarea></label
			>
			<p class="theme-text-muted">{$messages.drawingMashup.criterionHelp}</p>
		{:else if view.phase === 'drawing'}
			<p>{$messages.drawingMashup.drawHelp}</p>
			<nav class="flex gap-2" aria-label={$messages.drawingMashup.queue}>
				{#each view.assignments as art, i}<button
						class={`btn ${selected === i ? 'btn-primary' : 'btn-ghost'}`}
						aria-pressed={selected === i}
						onclick={() => (selected = i)}>{i + 1} {drafts[art.id]?.value ? '✓' : ''}</button
					>{/each}
			</nav>
			{#if active}<h3 class="text-xl font-bold">
					{drawingText(active.topic, 'topic', view.language)}
				</h3>
				{#key `${phaseKey}:${active.id}:${canvasVersion}`}<DrawingInput
						{disabled}
						initialDrawing={drafts[active.id]?.value as DrawingSubmission | null}
						showSubmit={false}
						onSubmit={() => {}}
						onChange={(value) => update(active.id, value)}
					/>{/key}
			{/if}
		{:else if view.phase === 'voting' && view.matchup}
			<h3 class="text-2xl font-bold">{drawingText(view.matchup.topic, 'topic', view.language)}</h3>
			<p class="text-xl">
				<strong>{$messages.drawingMashup.criterion}:</strong>
				{drawingText(view.matchup.criterion, 'criterion', view.language)}
			</p>
			<p>{$messages.drawingMashup.voteHelp}</p>
			{#each view.matchup.drawings as art, i}<button
					class={`card drawing-choice ${ballot.drawing_id === art.id ? 'selected' : ''}`}
					disabled={view.paused || art.own}
					aria-pressed={ballot.drawing_id === art.id}
					onclick={() => update('ballot', { ...ballot, drawing_id: art.id })}
					><strong
						>{String.fromCharCode(65 + i)}
						{art.own ? `· ${$messages.drawingMashup.own}` : ''}</strong
					><DrawingDisplay drawing={art.value} /></button
				>{/each}
			<button
				class="btn btn-ghost"
				aria-pressed={ballot.drawing_id === null}
				disabled={view.paused}
				onclick={() => update('ballot', { ...ballot, drawing_id: null })}
				>{$messages.drawingMashup.abstain}</button
			>
			<label class="commend"
				><input
					type="checkbox"
					checked={ballot.topic}
					disabled={view.paused || !view.matchup.can_commend_topic}
					onchange={(e) => update('ballot', { ...ballot, topic: e.currentTarget.checked })}
				/>{$messages.drawingMashup.commendTopic}</label
			>
			<label class="commend"
				><input
					type="checkbox"
					checked={ballot.criterion}
					disabled={view.paused || !view.matchup.can_commend_criterion}
					onchange={(e) => update('ballot', { ...ballot, criterion: e.currentTarget.checked })}
				/>{$messages.drawingMashup.commendCriterion}</label
			>
		{/if}
		<p role="status" class="theme-text-muted">
			{!connected && dirty
				? $messages.drawingMashup.unsaved
				: pending || dirty
					? $messages.drawingMashup.saving
					: $messages.drawingMashup.saved}
		</p>
		{#if ready}<p>{$messages.drawingMashup.ready}</p>{:else}<button
				class="btn btn-primary"
				disabled={!canFinish || view.paused || !connected || readyRequested}
				onclick={finish}>{$messages.drawingMashup.done}</button
			>{/if}
	{/if}
	{#if error}<p role="alert">
			{$messages.drawingMashup[error as 'error'] ?? $messages.drawingMashup.error}
		</p>{/if}
</section>

{#if organizer}
	{#key view.phase_id}
		<div>
			<button use:viewportPortal type="button" class="organizer-toggle" popovertarget={controlsId}>
				{$messages.gameplay.organizerControls}
			</button>
			<div
				id={controlsId}
				popover="auto"
				class="organizer-panel"
				role="region"
				aria-labelledby={`${controlsId}-heading`}
				ontoggle={(event) => {
					if (event.newState === 'closed') confirmAdvance = false;
				}}
			>
				<div class="mb-3 flex items-center justify-between gap-3">
					<h2 id={`${controlsId}-heading`} class="font-bold">
						{$messages.gameplay.organizerControls}
					</h2>
					<button
						type="button"
						class="organizer-close"
						popovertarget={controlsId}
						popovertargetaction="hide"
						aria-label={$messages.common.close}>×</button
					>
				</div>
				<div class="flex flex-col gap-2">
					<button
						class="btn btn-ghost"
						disabled={!connected || !!pending}
						onclick={() => control(view.paused ? 'resume' : 'pause')}
						>{view.paused ? $messages.drawingMashup.resume : $messages.drawingMashup.pause}</button
					><button
						class="btn btn-ghost"
						disabled={!connected || !!pending || dirty}
						onclick={() => control('advance')}
						>{confirmAdvance
							? $messages.drawingMashup.confirmAdvance
							: $messages.drawingMashup.advance}</button
					>
				</div>
			</div>
		</div>
	{/key}
{/if}

<style>
	.organizer-toggle,
	.organizer-panel {
		position: fixed;
		left: max(0.5rem, env(safe-area-inset-left));
		border: 1px solid var(--party-border);
		background: var(--party-surface-strong);
		color: var(--party-ink);
		box-shadow: 0 10px 26px rgba(15, 23, 42, 0.16);
		backdrop-filter: blur(12px);
	}
	.organizer-toggle {
		bottom: max(0.5rem, env(safe-area-inset-bottom));
		z-index: 70;
		min-height: 2.75rem;
		max-width: calc(100vw - 8rem);
		border-radius: 999px;
		padding: 0.65rem 0.85rem;
		font-size: 0.8rem;
		font-weight: 700;
	}
	.organizer-panel {
		top: auto;
		right: auto;
		bottom: calc(4.5rem + env(safe-area-inset-bottom));
		margin: 0;
		width: min(22rem, calc(100vw - 1rem - env(safe-area-inset-left) - env(safe-area-inset-right)));
		max-height: calc(100dvh - 5.5rem - env(safe-area-inset-top) - env(safe-area-inset-bottom));
		overflow-y: auto;
		overscroll-behavior: contain;
		border-radius: 1rem;
		padding: 1rem;
	}
	.organizer-close {
		flex-shrink: 0;
		width: 2.75rem;
		height: 2.75rem;
		border-radius: 0.75rem;
		font-size: 1.5rem;
	}
	.organizer-toggle:focus-visible,
	.organizer-close:focus-visible {
		outline: 2px solid var(--party-primary);
		outline-offset: 3px;
	}
	.organizer-toggle:hover,
	.organizer-close:hover {
		background: var(--party-soft-surface);
	}
	.drawing-choice {
		width: 100%;
		text-align: left;
		border: 3px solid transparent;
	}
	.drawing-choice.selected {
		border-color: var(--color-primary, #6366f1);
	}
	.drawing-choice:disabled {
		opacity: 0.55;
	}
	.commend {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		min-height: 3rem;
	}
	.commend input {
		width: 1.25rem;
		height: 1.25rem;
	}
</style>
