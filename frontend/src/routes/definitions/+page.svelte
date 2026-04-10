<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	const INPUT_KINDS: PlayerInputKind[] = [
		'none',
		'buzzer',
		'text',
		'number',
		'ordering',
		'radio',
		'checkbox'
	];
	const EVALUATION_TYPES: EvaluationType[] = [
		'none',
		'host_judged',
		'exact_text',
		'exact_number',
		'closest_number',
		'ordering_match'
	];
	const MEDIA_TYPES = ['image', 'audio', 'video'] as const;
	const IMAGE_REVEALS = ['none', 'blur_to_clear', 'blur_circle', 'zoom_out'] as const;

	let definitions = $state<DefinitionSummary[]>([]);
	let draft = $state<GameDefinition>(createEmptyDefinition());
	let selectedDefinitionId = $state<string | null>(null);
	let loadingList = $state(false);
	let loadingEditor = $state(false);
	let saving = $state(false);
	let statusMessage = $state('');
	let errorMessage = $state('');
	let uploadKey = $state<string | null>(null);
	let uploadError = $state('');
	let isNewDefinition = $state(true);

	onMount(async () => {
		await loadDefinitions();
	});

	function createEmptyDefinition(): GameDefinition {
		return {
			id: '',
			title: '',
			description: '',
			rounds: [createEmptyRound(1)]
		};
	}

	function createEmptyRound(index: number): RoundDefinition {
		return {
			id: `round_${index}`,
			title: `Round ${index}`,
			steps: [createEmptyStep(index, 1)]
		};
	}

	function createEmptyStep(roundIndex: number, stepIndex: number): StepDefinition {
		return {
			id: `step_${roundIndex}_${stepIndex}`,
			title: `Step ${stepIndex}`,
			body: '',
			timer: {
				seconds: 30,
				enforced: false
			},
			player_input: {
				kind: 'text',
				prompt: '',
				placeholder: '',
				options: [],
				min_value: undefined,
				max_value: undefined,
				step: undefined
			},
			evaluation: {
				type_: 'host_judged',
				points: 1,
				answer: ''
			},
			host_behavior: {
				reveal_answers: true,
				show_submissions: true,
				allow_custom_points: true
			}
		};
	}

	async function loadDefinitions() {
		loadingList = true;
		errorMessage = '';
		const response = await fetch('/api/v1/definitions');
		loadingList = false;
		if (!response.ok) {
			errorMessage = 'Could not load definitions.';
			return;
		}
		definitions = await response.json();
	}

	async function openDefinition(definitionId: string) {
		selectedDefinitionId = definitionId;
		isNewDefinition = false;
		errorMessage = '';
		statusMessage = '';
		loadingEditor = true;
		const response = await fetch(`/api/v1/definitions/${definitionId}`);
		loadingEditor = false;
		if (!response.ok) {
			errorMessage = `Could not load definition "${definitionId}".`;
			return;
		}
		draft = structuredClone(await response.json());
	}

	function startNewDefinition() {
		selectedDefinitionId = null;
		isNewDefinition = true;
		errorMessage = '';
		statusMessage = '';
		uploadError = '';
		draft = createEmptyDefinition();
	}

	function addRound() {
		draft.rounds.push(createEmptyRound(draft.rounds.length + 1));
	}

	function removeRound(roundIndex: number) {
		if (draft.rounds.length === 1) {
			draft.rounds = [createEmptyRound(1)];
			return;
		}
		draft.rounds.splice(roundIndex, 1);
	}

	function moveRound(roundIndex: number, direction: -1 | 1) {
		const targetIndex = roundIndex + direction;
		if (targetIndex < 0 || targetIndex >= draft.rounds.length) {
			return;
		}
		const rounds = [...draft.rounds];
		[rounds[roundIndex], rounds[targetIndex]] = [rounds[targetIndex], rounds[roundIndex]];
		draft.rounds = rounds;
	}

	function addStep(roundIndex: number) {
		const round = draft.rounds[roundIndex];
		round.steps.push(createEmptyStep(roundIndex + 1, round.steps.length + 1));
	}

	function removeStep(roundIndex: number, stepIndex: number) {
		const round = draft.rounds[roundIndex];
		if (round.steps.length === 1) {
			round.steps = [createEmptyStep(roundIndex + 1, 1)];
			return;
		}
		round.steps.splice(stepIndex, 1);
	}

	function moveStep(roundIndex: number, stepIndex: number, direction: -1 | 1) {
		const steps = [...draft.rounds[roundIndex].steps];
		const targetIndex = stepIndex + direction;
		if (targetIndex < 0 || targetIndex >= steps.length) {
			return;
		}
		[steps[stepIndex], steps[targetIndex]] = [steps[targetIndex], steps[stepIndex]];
		draft.rounds[roundIndex].steps = steps;
	}

	function setPlayerInputKind(step: StepDefinition, kind: PlayerInputKind) {
		step.player_input.kind = kind;
		if (kind === 'ordering' || kind === 'radio' || kind === 'checkbox') {
			if (step.player_input.options.length < 2) {
				step.player_input.options = ['Option 1', 'Option 2'];
			}
			if (kind === 'ordering' && !Array.isArray(step.evaluation.answer)) {
				step.evaluation.answer = [...step.player_input.options];
			}
			if (kind === 'radio' && Array.isArray(step.evaluation.answer)) {
				step.evaluation.answer = step.player_input.options[0] ?? '';
			}
		} else {
			step.player_input.options = [];
		}
		if (kind !== 'number') {
			step.player_input.min_value = undefined;
			step.player_input.max_value = undefined;
			step.player_input.step = undefined;
		}
		if (kind === 'buzzer') {
			step.evaluation.type_ = 'host_judged';
		}
	}

	function setEvaluationType(step: StepDefinition, evaluationType: EvaluationType) {
		step.evaluation.type_ = evaluationType;
		if (evaluationType === 'ordering_match') {
			step.evaluation.answer = [...step.player_input.options];
			return;
		}
		if (evaluationType === 'exact_number' || evaluationType === 'closest_number') {
			step.evaluation.answer = Number(step.evaluation.answer ?? 0);
			return;
		}
		if (Array.isArray(step.evaluation.answer)) {
			step.evaluation.answer = '';
		}
	}

	function addInputOption(step: StepDefinition) {
		step.player_input.options.push(`Option ${step.player_input.options.length + 1}`);
		if (step.evaluation.type_ === 'ordering_match') {
			step.evaluation.answer = [...step.player_input.options];
		}
	}

	function removeInputOption(step: StepDefinition, optionIndex: number) {
		step.player_input.options.splice(optionIndex, 1);
		if (step.evaluation.type_ === 'ordering_match') {
			step.evaluation.answer = [...step.player_input.options];
		}
	}

	function addMedia(step: StepDefinition) {
		step.media = {
			type_: 'image',
			src: '',
			reveal: 'none',
			loop: false
		};
	}

	function removeMedia(step: StepDefinition) {
		step.media = undefined;
	}

	function updateMediaType(step: StepDefinition, mediaType: (typeof MEDIA_TYPES)[number]) {
		if (!step.media) {
			addMedia(step);
		}
		if (!step.media) {
			return;
		}
		step.media.type_ = mediaType;
		if (mediaType !== 'image') {
			step.media.reveal = 'none';
		}
	}

	function getOrderingAnswer(step: StepDefinition): string[] {
		return Array.isArray(step.evaluation.answer)
			? step.evaluation.answer.map((value) => String(value))
			: [...step.player_input.options];
	}

	function setOrderingAnswer(step: StepDefinition, optionIndex: number, value: string) {
		const answer = getOrderingAnswer(step);
		answer[optionIndex] = value;
		step.evaluation.answer = answer;
	}

	function getTextAnswer(step: StepDefinition): string {
		if (Array.isArray(step.evaluation.answer)) {
			return '';
		}
		return String(step.evaluation.answer ?? '');
	}

	function getNumberAnswer(step: StepDefinition): number | undefined {
		const value = Number(step.evaluation.answer);
		return Number.isFinite(value) ? value : undefined;
	}

	function buildPayload(): GameDefinition {
		return {
			id: draft.id.trim(),
			title: draft.title.trim(),
			description: draft.description?.trim() || undefined,
			rounds: draft.rounds.map((round) => ({
				id: round.id.trim(),
				title: round.title?.trim() || undefined,
				steps: round.steps.map((step) => ({
					id: step.id.trim(),
					title: step.title.trim(),
					body: step.body?.trim() || undefined,
					timer: {
						seconds: step.timer.seconds ?? undefined,
						enforced: step.timer.enforced
					},
					player_input: {
						kind: step.player_input.kind,
						prompt: step.player_input.prompt?.trim() || undefined,
						placeholder: step.player_input.placeholder?.trim() || undefined,
						options: step.player_input.options.map((option) => option.trim()).filter(Boolean),
						min_value: step.player_input.min_value ?? undefined,
						max_value: step.player_input.max_value ?? undefined,
						step: step.player_input.step ?? undefined
					},
					evaluation: {
						type_: step.evaluation.type_,
						points: step.evaluation.points,
						answer: normalizeAnswer(step)
					},
					host_behavior: {
						reveal_answers: step.host_behavior.reveal_answers,
						show_submissions: step.host_behavior.show_submissions,
						allow_custom_points: step.host_behavior.allow_custom_points
					},
					media:
						step.media && step.media.src.trim()
							? {
									type_: step.media.type_,
									src: step.media.src.trim(),
									reveal: step.media.reveal,
									loop: step.media.loop
								}
							: undefined
				}))
			}))
		};
	}

	function normalizeAnswer(step: StepDefinition): unknown {
		if (step.evaluation.type_ === 'ordering_match') {
			return getOrderingAnswer(step)
				.map((value) => value.trim())
				.filter(Boolean);
		}
		if (step.evaluation.type_ === 'exact_number' || step.evaluation.type_ === 'closest_number') {
			return step.evaluation.answer === '' ? null : Number(step.evaluation.answer);
		}
		const value = getTextAnswer(step).trim();
		return value || null;
	}

	async function saveDefinition() {
		saving = true;
		errorMessage = '';
		statusMessage = '';
		const payload = buildPayload();
		const endpoint = isNewDefinition ? '/api/v1/definitions' : `/api/v1/definitions/${draft.id}`;
		const response = await fetch(endpoint, {
			method: isNewDefinition ? 'POST' : 'PUT',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(payload)
		});
		saving = false;
		if (!response.ok) {
			const detail = await readErrorDetail(response);
			errorMessage = detail || 'Could not save definition.';
			return;
		}
		draft = structuredClone(await response.json());
		selectedDefinitionId = draft.id;
		isNewDefinition = false;
		statusMessage = 'Definition saved.';
		await loadDefinitions();
	}

	async function uploadMedia(
		event: Event,
		step: StepDefinition,
		roundIndex: number,
		stepIndex: number
	) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) {
			return;
		}
		if (!step.media) {
			addMedia(step);
		}
		if (!step.media) {
			return;
		}
		const key = `${roundIndex}-${stepIndex}`;
		uploadKey = key;
		uploadError = '';
		const response = await fetch(
			`/api/v1/media?kind=${step.media.type_}&filename=${encodeURIComponent(file.name)}`,
			{
				method: 'POST',
				headers: {
					'Content-Type': file.type || 'application/octet-stream'
				},
				body: file
			}
		);
		uploadKey = null;
		if (!response.ok) {
			uploadError = (await readErrorDetail(response)) || 'Could not upload media.';
			input.value = '';
			return;
		}
		const asset: MediaAsset = await response.json();
		step.media.src = asset.public_url;
		input.value = '';
	}

	async function readErrorDetail(response: Response): Promise<string> {
		try {
			const payload = await response.json();
			if (typeof payload?.detail === 'string') {
				return payload.detail;
			}
		} catch {
			return '';
		}
		return '';
	}
</script>

<div class="flex flex-wrap items-start justify-between gap-4">
	<div>
		<h1 class="page-title text-left">Manage Definitions</h1>
		<p class="page-subtitle text-left">
			Create new game definitions, edit existing ones, and attach media without leaving the app.
		</p>
	</div>
	<div class="flex flex-wrap gap-3">
		<button class="btn btn-ghost text-lg" onclick={() => goto('/create')}
			>Back to Create Game</button
		>
		<button class="btn btn-accent text-lg" onclick={startNewDefinition}>New Definition</button>
	</div>
</div>

<div class="stack-lg">
	<section class="card stack-md">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<h2 class="label-title text-2xl">Saved Definitions</h2>
			{#if loadingList}
				<span class="text-sm text-slate-500">Refreshing...</span>
			{/if}
		</div>
		{#if definitions.length === 0}
			<p class="text-slate-600">No saved definitions yet. Start with a blank draft.</p>
		{:else}
			<div class="grid gap-3">
				{#each definitions as definition}
					<button
						class={`card w-full text-left transition ${
							selectedDefinitionId === definition.id ? 'ring-2 ring-sky-300' : ''
						}`}
						onclick={() => openDefinition(definition.id)}
					>
						<div class="flex items-center justify-between gap-4">
							<div>
								<div class="text-xl font-bold">{definition.title}</div>
								<div class="text-sm text-slate-600">{definition.id}</div>
							</div>
							<span class="badge bg-sky-100 text-sky-800">Open</span>
						</div>
						{#if definition.description}
							<p class="mt-2 text-sm text-slate-600">{definition.description}</p>
						{/if}
					</button>
				{/each}
			</div>
		{/if}
	</section>

	<section class="card stack-md">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div>
				<h2 class="label-title text-2xl">{isNewDefinition ? 'New Definition Draft' : 'Editor'}</h2>
				<p class="text-sm text-slate-600">
					{isNewDefinition
						? 'Build a new definition and save it when it is ready.'
						: `Editing ${draft.title || draft.id}.`}
				</p>
			</div>
			<button
				class="btn btn-primary text-lg"
				onclick={saveDefinition}
				disabled={saving || loadingEditor}
			>
				{saving ? 'Saving...' : isNewDefinition ? 'Create Definition' : 'Save Changes'}
			</button>
		</div>

		{#if errorMessage}
			<div class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-red-700">
				{errorMessage}
			</div>
		{/if}
		{#if statusMessage}
			<div class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-700">
				{statusMessage}
			</div>
		{/if}
		{#if uploadError}
			<div class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-700">
				{uploadError}
			</div>
		{/if}
		{#if loadingEditor}
			<p class="text-slate-500">Loading definition...</p>
		{:else}
			<div class="grid gap-3">
				<label class="input-wrap">
					<span class="label-title">Definition id</span>
					<input bind:value={draft.id} class="input text-lg" placeholder="music_night" />
				</label>
				<label class="input-wrap">
					<span class="label-title">Title</span>
					<input bind:value={draft.title} class="input text-lg" placeholder="Music Night" />
				</label>
				<label class="input-wrap">
					<span class="label-title">Description</span>
					<textarea
						bind:value={draft.description}
						class="input min-h-28 text-lg"
						placeholder="What kind of experience should hosts expect?"
					></textarea>
				</label>
			</div>

			<div class="mt-4 stack-md">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<h3 class="label-title text-2xl">Rounds</h3>
					<button class="btn btn-accent text-lg" onclick={addRound}>Add Round</button>
				</div>

				{#each draft.rounds as round, roundIndex}
					<div class="rounded-3xl border border-slate-200 bg-white/70 p-4">
						<div class="flex flex-wrap items-center justify-between gap-3">
							<div>
								<h4 class="label-title text-xl">Round {roundIndex + 1}</h4>
								<p class="text-sm text-slate-600">{round.steps.length} steps</p>
							</div>
							<div class="flex flex-wrap gap-2">
								<button class="btn btn-ghost text-sm" onclick={() => moveRound(roundIndex, -1)}>
									Move Up
								</button>
								<button class="btn btn-ghost text-sm" onclick={() => moveRound(roundIndex, 1)}>
									Move Down
								</button>
								<button class="btn btn-danger text-sm" onclick={() => removeRound(roundIndex)}>
									Remove Round
								</button>
							</div>
						</div>

						<div class="mt-4 grid gap-3">
							<label class="input-wrap">
								<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
									>Round id</span
								>
								<input bind:value={round.id} class="input text-lg" />
							</label>
							<label class="input-wrap">
								<span class="text-sm font-bold uppercase tracking-wide text-slate-500">Title</span>
								<input bind:value={round.title} class="input text-lg" />
							</label>
						</div>

						<div class="mt-5 stack-md">
							<div class="flex flex-wrap items-center justify-between gap-3">
								<h5 class="label-title text-xl">Steps</h5>
								<button class="btn btn-primary text-sm" onclick={() => addStep(roundIndex)}
									>Add Step</button
								>
							</div>

							{#each round.steps as step, stepIndex}
								<div class="rounded-3xl border border-slate-200 bg-slate-50/80 p-4">
									<div class="flex flex-wrap items-center justify-between gap-3">
										<div>
											<h6 class="label-title text-xl">Step {stepIndex + 1}</h6>
											<p class="text-sm text-slate-600">
												{step.player_input.kind} input · {step.evaluation.type_} scoring
											</p>
										</div>
										<div class="flex flex-wrap gap-2">
											<button
												class="btn btn-ghost text-sm"
												onclick={() => moveStep(roundIndex, stepIndex, -1)}
											>
												Move Up
											</button>
											<button
												class="btn btn-ghost text-sm"
												onclick={() => moveStep(roundIndex, stepIndex, 1)}
											>
												Move Down
											</button>
											<button
												class="btn btn-danger text-sm"
												onclick={() => removeStep(roundIndex, stepIndex)}
											>
												Remove Step
											</button>
										</div>
									</div>

									<div class="mt-4 grid gap-3">
										<label class="input-wrap">
											<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
												>Step id</span
											>
											<input bind:value={step.id} class="input text-lg" />
										</label>
										<label class="input-wrap">
											<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
												>Title</span
											>
											<input bind:value={step.title} class="input text-lg" />
										</label>
										<label class="input-wrap">
											<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
												>Body</span
											>
											<textarea bind:value={step.body} class="input min-h-24 text-lg"></textarea>
										</label>
									</div>

									<div class="mt-4 grid gap-3 md:grid-cols-2">
										<label class="input-wrap">
											<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
												>Input kind</span
											>
											<div class="select-shell">
												<select
													class="input select-input text-lg"
													value={step.player_input.kind}
													onchange={(event) =>
														setPlayerInputKind(
															step,
															(event.currentTarget as HTMLSelectElement).value as PlayerInputKind
														)}
												>
													{#each INPUT_KINDS as kind}
														<option value={kind}>{kind}</option>
													{/each}
												</select>
												<span class="select-chevron" aria-hidden="true">▾</span>
											</div>
										</label>
										<label class="input-wrap">
											<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
												Evaluation
											</span>
											<div class="select-shell">
												<select
													class="input select-input text-lg"
													value={step.evaluation.type_}
													onchange={(event) =>
														setEvaluationType(
															step,
															(event.currentTarget as HTMLSelectElement).value as EvaluationType
														)}
												>
													{#each EVALUATION_TYPES as evaluationType}
														<option value={evaluationType}>{evaluationType}</option>
													{/each}
												</select>
												<span class="select-chevron" aria-hidden="true">▾</span>
											</div>
										</label>
										<label class="input-wrap">
											<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
												>Timer seconds</span
											>
											<input
												bind:value={step.timer.seconds}
												type="number"
												min="0"
												class="input text-lg"
											/>
										</label>
										<label
											class="flex items-center justify-between gap-4 rounded-2xl bg-white/80 px-4 py-3"
										>
											<div>
												<p class="text-lg font-bold">Enforced timer</p>
												<p class="text-sm text-slate-600">Automatically close the step at zero.</p>
											</div>
											<input bind:checked={step.timer.enforced} type="checkbox" class="h-5 w-5" />
										</label>
									</div>

									<div class="mt-4 grid gap-3 md:grid-cols-2">
										<label class="input-wrap">
											<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
												>Input prompt</span
											>
											<input bind:value={step.player_input.prompt} class="input text-lg" />
										</label>
										<label class="input-wrap">
											<span class="text-sm font-bold uppercase tracking-wide text-slate-500">
												Placeholder
											</span>
											<input bind:value={step.player_input.placeholder} class="input text-lg" />
										</label>
										<label class="input-wrap">
											<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
												>Points</span
											>
											<input
												bind:value={step.evaluation.points}
												type="number"
												class="input text-lg"
											/>
										</label>
									</div>

									{#if step.player_input.kind === 'number'}
										<div class="mt-4 grid gap-3 md:grid-cols-3">
											<label class="input-wrap">
												<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
													>Min value</span
												>
												<input
													bind:value={step.player_input.min_value}
													type="number"
													class="input text-lg"
												/>
											</label>
											<label class="input-wrap">
												<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
													>Max value</span
												>
												<input
													bind:value={step.player_input.max_value}
													type="number"
													class="input text-lg"
												/>
											</label>
											<label class="input-wrap">
												<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
													>Slider step</span
												>
												<input
													bind:value={step.player_input.step}
													type="number"
													min="0"
													class="input text-lg"
												/>
											</label>
										</div>
									{/if}

									{#if ['ordering', 'radio', 'checkbox'].includes(step.player_input.kind)}
										<div class="mt-4 rounded-2xl bg-white/80 p-4">
											<div class="flex flex-wrap items-center justify-between gap-3">
												<p class="text-lg font-bold">
													{step.player_input.kind === 'ordering'
														? 'Ordering options'
														: step.player_input.kind === 'radio'
															? 'Radio button options'
															: 'Checkbox options'}
												</p>
												<button class="btn btn-ghost text-sm" onclick={() => addInputOption(step)}>
													Add Option
												</button>
											</div>
											<div class="mt-3 grid gap-3">
												{#each step.player_input.options as option, optionIndex}
													<div class="grid gap-3 md:grid-cols-[1fr_auto]">
														<input
															bind:value={step.player_input.options[optionIndex]}
															class="input text-lg"
														/>
														<button
															class="btn btn-danger text-sm"
															onclick={() => removeInputOption(step, optionIndex)}
														>
															Remove
														</button>
													</div>
												{/each}
											</div>
										</div>
									{/if}

									{#if step.evaluation.type_ === 'ordering_match'}
										<div class="mt-4 rounded-2xl bg-white/80 p-4">
											<p class="text-lg font-bold">Correct order</p>
											<div class="mt-3 grid gap-3">
												{#each getOrderingAnswer(step) as answerValue, optionIndex}
													<input
														value={answerValue}
														class="input text-lg"
														oninput={(event) =>
															setOrderingAnswer(
																step,
																optionIndex,
																(event.currentTarget as HTMLInputElement).value
															)}
													/>
												{/each}
											</div>
										</div>
									{:else if step.evaluation.type_ === 'exact_number' || step.evaluation.type_ === 'closest_number'}
										<label class="input-wrap mt-4">
											<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
												>Correct number</span
											>
											<input
												class="input text-lg"
												type="number"
												value={getNumberAnswer(step)}
												oninput={(event) =>
													(step.evaluation.answer = (
														event.currentTarget as HTMLInputElement
													).value)}
											/>
										</label>
									{:else if step.evaluation.type_ !== 'none'}
										<label class="input-wrap mt-4">
											<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
												>Answer / rubric</span
											>
											<input
												class="input text-lg"
												value={getTextAnswer(step)}
												oninput={(event) =>
													(step.evaluation.answer = (
														event.currentTarget as HTMLInputElement
													).value)}
											/>
										</label>
									{/if}

									<div class="mt-4 rounded-2xl bg-white/80 p-4">
										<p class="text-lg font-bold">Host controls</p>
										<div class="mt-3 grid gap-3 md:grid-cols-3">
											<label
												class="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3"
											>
												<span class="text-sm font-semibold">Reveal answers</span>
												<input
													bind:checked={step.host_behavior.reveal_answers}
													type="checkbox"
													class="h-5 w-5"
												/>
											</label>
											<label
												class="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3"
											>
												<span class="text-sm font-semibold">Show submissions</span>
												<input
													bind:checked={step.host_behavior.show_submissions}
													type="checkbox"
													class="h-5 w-5"
												/>
											</label>
											<label
												class="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3"
											>
												<span class="text-sm font-semibold">Custom points</span>
												<input
													bind:checked={step.host_behavior.allow_custom_points}
													type="checkbox"
													class="h-5 w-5"
												/>
											</label>
										</div>
									</div>

									<div class="mt-4 rounded-2xl bg-white/80 p-4">
										<div class="flex flex-wrap items-center justify-between gap-3">
											<p class="text-lg font-bold">Media</p>
											{#if step.media}
												<button class="btn btn-danger text-sm" onclick={() => removeMedia(step)}>
													Remove Media
												</button>
											{:else}
												<button class="btn btn-ghost text-sm" onclick={() => addMedia(step)}
													>Add Media</button
												>
											{/if}
										</div>

										{#if step.media}
											<div class="mt-3 grid gap-3">
												<label class="input-wrap">
													<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
														>Media type</span
													>
													<div class="select-shell">
														<select
															class="input select-input text-lg"
															value={step.media.type_}
															onchange={(event) =>
																updateMediaType(
																	step,
																	(event.currentTarget as HTMLSelectElement)
																		.value as (typeof MEDIA_TYPES)[number]
																)}
														>
															{#each MEDIA_TYPES as mediaType}
																<option value={mediaType}>{mediaType}</option>
															{/each}
														</select>
														<span class="select-chevron" aria-hidden="true">▾</span>
													</div>
												</label>

												<label class="input-wrap">
													<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
														>Source URL</span
													>
													<input
														bind:value={step.media.src}
														class="input text-lg"
														placeholder="/api/v1/media/..."
													/>
												</label>

												{#if step.media.type_ === 'image'}
													<label class="input-wrap">
														<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
															>Reveal mode</span
														>
														<div class="select-shell">
															<select
																bind:value={step.media.reveal}
																class="input select-input text-lg"
															>
																{#each IMAGE_REVEALS as revealMode}
																	<option value={revealMode}>{revealMode}</option>
																{/each}
															</select>
															<span class="select-chevron" aria-hidden="true">▾</span>
														</div>
													</label>
												{/if}

												<label
													class="flex items-center justify-between gap-4 rounded-2xl bg-slate-50 px-4 py-3"
												>
													<div>
														<p class="text-lg font-bold">Loop media</p>
														<p class="text-sm text-slate-600">
															Useful for short ambient clips and repeatable audio.
														</p>
													</div>
													<input bind:checked={step.media.loop} type="checkbox" class="h-5 w-5" />
												</label>

												<label class="input-wrap">
													<span class="text-sm font-bold uppercase tracking-wide text-slate-500"
														>Upload file</span
													>
													<input
														type="file"
														class="input text-base file:mr-4 file:rounded-xl file:border-0 file:bg-sky-100 file:px-3 file:py-2 file:font-semibold file:text-sky-700"
														onchange={(event) => uploadMedia(event, step, roundIndex, stepIndex)}
													/>
												</label>

												{#if uploadKey === `${roundIndex}-${stepIndex}`}
													<p class="text-sm text-sky-700">Uploading media...</p>
												{/if}

												{#if step.media.src}
													<div class="rounded-2xl bg-slate-50 p-3 text-sm text-slate-600">
														Saved media source: {step.media.src}
													</div>
												{/if}
											</div>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</section>
</div>
