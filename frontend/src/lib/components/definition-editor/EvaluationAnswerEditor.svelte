<script lang="ts">
	import { messages } from '$lib/i18n';
	import MapPointEditor from '$lib/components/MapPointEditor.svelte';
	import OrderingList from '$lib/components/OrderingList.svelte';
	import {
		buildDefaultMapDistanceAnswer,
		DEFAULT_MAP_CONFIG,
		getExactTextMaxDistance,
		getMapDistanceAnswer,
		getNumberAnswer,
		getNumberToleranceBands,
		normalizeMapDistanceAnswerForMode,
		getTextAnswer,
		getTextAnswers
	} from './helpers';

	type Props = {
		step: StepDefinition;
		orderedAnswer: string[];
		onSetOrderingAnswerOrder: (step: StepDefinition, values: string[]) => void;
	};

	let { step, orderedAnswer, onSetOrderingAnswerOrder }: Props = $props();
	let previewPlayerBaseLayer = $state(false);
	let draftMapConfig = $state<MapInputConfig | null>(null);

	const textAnswers = $derived(getTextAnswers(step));
	const mapConfig = $derived(step.player_input.map ?? DEFAULT_MAP_CONFIG);
	const editableMapConfig = $derived(draftMapConfig ?? mapConfig);
	const mapAnswer = $derived(
		getMapDistanceAnswer(step) ?? buildDefaultMapDistanceAnswer(mapConfig)
	);
	const numberBands = $derived(getNumberToleranceBands(step));

	function setTextAnswer(index: number, value: string) {
		const answers = [...textAnswers];
		answers[index] = value;
		step.evaluation.answer = answers;
	}

	function addTextAnswer() {
		step.evaluation.answer = [...textAnswers, ''];
	}

	function removeTextAnswer(index: number) {
		const answers = textAnswers.filter((_, answerIndex) => answerIndex !== index);
		step.evaluation.answer = answers.length > 0 ? answers : [''];
	}

	function setMapAnswer(answer: MapDistanceAnswer) {
		const normalized = normalizeMapDistanceAnswerForMode(answer, mapConfig);
		step.evaluation.answer = normalized;
		step.evaluation.points = normalized.max_points;
	}

	function updateMapAnswer(updates: Partial<MapDistanceAnswer>) {
		setMapAnswer({ ...mapAnswer, ...updates });
	}

	function updateMapConfig(updates: Partial<MapInputConfig>) {
		step.player_input.map = {
			...mapConfig,
			...updates
		};
		if (draftMapConfig) {
			draftMapConfig = {
				...draftMapConfig,
				...updates
			};
		}
	}

	function applyDraftMapBounds() {
		if (!draftMapConfig) {
			return;
		}
		step.player_input.map = draftMapConfig;
		draftMapConfig = null;
	}

	function setCorrectMapPoint(point: MapPoint) {
		updateMapAnswer({ correct_point: point });
	}

	function updateMapBand(index: number, updates: Partial<MapDistanceBand>) {
		const bands = [...(mapAnswer.bands ?? [])];
		bands[index] = { ...bands[index], ...updates };
		updateMapAnswer({ bands });
	}

	function addMapBand() {
		const lastBand = mapAnswer.bands?.at(-1);
		updateMapAnswer({
			bands: [
				...(mapAnswer.bands ?? []),
				{
					distance_m: lastBand ? lastBand.distance_m * 2 : 1000,
					points: Math.max(1, Math.floor(mapAnswer.max_points / 2)),
					label: ''
				}
			]
		});
	}

	function removeMapBand(index: number) {
		updateMapAnswer({
			bands: (mapAnswer.bands ?? []).filter((_, bandIndex) => bandIndex !== index)
		});
	}

	function updateNumberBand(index: number, updates: Partial<NumberToleranceBand>) {
		const bands = [...numberBands];
		bands[index] = { ...bands[index], ...updates };
		step.evaluation.number_bands = bands;
	}

	function addNumberBand() {
		const lastBand = numberBands.at(-1);
		step.evaluation.number_bands = [
			...numberBands,
			{
				distance: lastBand ? lastBand.distance * 2 : 5,
				points: Math.max(1, step.evaluation.points - numberBands.length - 1),
				label: ''
			}
		];
	}

	function removeNumberBand(index: number) {
		step.evaluation.number_bands = numberBands.filter((_, bandIndex) => bandIndex !== index);
	}

	function applyMapScoringPreset(kind: 'street' | 'city' | 'country') {
		if (kind === 'street') {
			setMapAnswer({
				...mapAnswer,
				scoring_mode: 'bands',
				max_points: 5,
				zero_distance_m: null,
				full_credit_distance_m: null,
				bands: [
					{ distance_m: 100, points: 5, label: 'Exact block' },
					{ distance_m: 500, points: 3, label: 'Close' },
					{ distance_m: 1500, points: 1, label: 'Nearby' }
				]
			});
			return;
		}
		if (kind === 'city') {
			setMapAnswer({
				...mapAnswer,
				scoring_mode: 'bands',
				max_points: 5,
				zero_distance_m: null,
				full_credit_distance_m: null,
				bands: [
					{ distance_m: 1000, points: 5, label: 'Same area' },
					{ distance_m: 5000, points: 3, label: 'Same city' },
					{ distance_m: 20_000, points: 1, label: 'Same region' }
				]
			});
			return;
		}
		setMapAnswer({
			...mapAnswer,
			scoring_mode: 'linear',
			max_points: 5,
			zero_distance_m: 1_000_000,
			full_credit_distance_m: 25_000,
			bands: mapAnswer.bands ?? []
		});
	}

	function setMapScoringMode(scoringMode: MapDistanceAnswer['scoring_mode']) {
		if (scoringMode === 'bands') {
			updateMapAnswer({
				scoring_mode: 'bands',
				zero_distance_m: null,
				full_credit_distance_m: null,
				bands:
					mapAnswer.bands && mapAnswer.bands.length > 0
						? mapAnswer.bands
						: [{ distance_m: 1000, points: mapAnswer.max_points, label: '' }]
			});
			return;
		}
		updateMapAnswer({
			scoring_mode: 'linear',
			zero_distance_m: mapAnswer.zero_distance_m ?? 50_000,
			full_credit_distance_m: mapAnswer.full_credit_distance_m ?? 500
		});
	}
</script>

{#if step.evaluation.type_ === 'ordering_match'}
	<div class="grid gap-3">
		<p class="editor-text-muted text-sm font-semibold">{$messages.editor.correctOrderHelp}</p>
		<OrderingList
			items={orderedAnswer}
			variant="editor"
			dragLabel={$messages.editor.dragOrderItem}
			moveUpLabel={$messages.editor.moveOrderItemUp}
			moveDownLabel={$messages.editor.moveOrderItemDown}
			onReorder={(items) => onSetOrderingAnswerOrder(step, items)}
		/>
	</div>
{:else if step.evaluation.type_ === 'exact_number' || step.evaluation.type_ === 'closest_number'}
	<div class="grid gap-4">
		<div class="grid gap-3 md:grid-cols-[minmax(0,1fr)_12rem]">
			<label class="input-wrap">
				<span class="editor-text-muted text-sm font-bold uppercase tracking-wide">
					{$messages.editor.correctNumber}
				</span>
				<input
					class="input text-lg"
					type="number"
					value={getNumberAnswer(step)}
					oninput={(event) =>
						(step.evaluation.answer = (event.currentTarget as HTMLInputElement).value)}
				/>
			</label>
			<div class="editor-nested-panel editor-text-muted rounded-2xl border p-4 text-sm">
				<p class="editor-text font-bold">{$messages.editor.scoringSummary}</p>
				<p class="mt-2">
					{step.evaluation.type_ === 'exact_number'
						? $messages.editor.exactNumberSummary
						: $messages.editor.closestNumberSummary}
				</p>
			</div>
		</div>
		{#if step.evaluation.type_ === 'closest_number'}
			<div class="editor-nested-panel rounded-2xl border p-4">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div>
						<p class="editor-text font-bold">{$messages.editor.numberBands}</p>
						<p class="editor-text-muted mt-1 text-sm">{$messages.editor.numberBandsHelp}</p>
					</div>
					<button type="button" class="btn btn-ghost text-sm" onclick={addNumberBand}>
						{$messages.editor.addNumberBand}
					</button>
				</div>
				{#if numberBands.length > 0}
					<div class="mt-3 grid gap-3">
						{#each numberBands as band, index}
							<div
								class="editor-muted-panel grid gap-2 rounded-xl border p-3 md:grid-cols-[1fr_1fr_minmax(0,1.4fr)_auto] md:items-end"
							>
								<label class="input-wrap">
									<span class="editor-text-muted text-xs font-bold uppercase tracking-wide">
										{$messages.editor.numberBandDistance}
									</span>
									<input
										class="input"
										type="number"
										min="0"
										value={band.distance}
										oninput={(event) =>
											updateNumberBand(index, {
												distance: Number((event.currentTarget as HTMLInputElement).value)
											})}
									/>
								</label>
								<label class="input-wrap">
									<span class="editor-text-muted text-xs font-bold uppercase tracking-wide">
										{$messages.editor.points}
									</span>
									<input
										class="input"
										type="number"
										min="0"
										step="1"
										value={band.points}
										oninput={(event) =>
											updateNumberBand(index, {
												points: Number((event.currentTarget as HTMLInputElement).value)
											})}
									/>
								</label>
								<label class="input-wrap">
									<span class="editor-text-muted text-xs font-bold uppercase tracking-wide">
										{$messages.editor.numberBandLabel}
									</span>
									<input
										class="input"
										type="text"
										value={band.label ?? ''}
										oninput={(event) =>
											updateNumberBand(index, {
												label: (event.currentTarget as HTMLInputElement).value
											})}
									/>
								</label>
								<button
									type="button"
									class="btn btn-ghost text-sm"
									onclick={() => removeNumberBand(index)}
								>
									{$messages.editor.removeNumberBand}
								</button>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	</div>
{:else if step.evaluation.type_ === 'multi_select_weighted'}
	<div class="editor-nested-panel editor-text-muted rounded-2xl border p-4 text-sm">
		<p class="editor-text font-bold">{$messages.editor.configureScoresAbove}</p>
		<p class="mt-2">{$messages.editor.configurePointsAboveHelp}</p>
	</div>
{:else if step.evaluation.type_ === 'map_distance'}
	<div class="grid gap-4">
		<div class="grid gap-3">
			<div>
				<p class="editor-text-muted text-sm font-bold uppercase tracking-wide">
					{$messages.editor.mapLockedArea} / {$messages.editor.mapCorrectPoint}
				</p>
				<p class="editor-text-muted mt-1 text-sm">
					{$messages.editor.mapLockedAreaHelp}
					{$messages.editor.mapCorrectPointHelp}
				</p>
			</div>
			<label class="input-wrap md:max-w-xs">
				<span class="editor-text-muted text-sm font-bold uppercase tracking-wide">
					{$messages.editor.mapPlayerBaseLayer}
				</span>
				<select
					class="input text-lg"
					value={mapConfig.base_layer ?? 'osm'}
					onchange={(event) =>
						updateMapConfig({
							base_layer: (event.currentTarget as HTMLSelectElement)
								.value as MapInputConfig['base_layer']
						})}
				>
					<option value="osm">{$messages.editor.mapBaseLayerOsm}</option>
					<option value="light_nolabels">{$messages.editor.mapBaseLayerLightNoLabels}</option>
				</select>
				<span class="editor-text-muted text-sm">{$messages.editor.mapPlayerBaseLayerHelp}</span>
			</label>
			<button
				type="button"
				class="btn btn-ghost w-fit text-sm"
				onpointerdown={() => (previewPlayerBaseLayer = true)}
				onpointerup={() => (previewPlayerBaseLayer = false)}
				onpointerleave={() => (previewPlayerBaseLayer = false)}
				onblur={() => (previewPlayerBaseLayer = false)}
			>
				{$messages.editor.mapPreviewPlayerBaseLayer}
			</button>
			<div class="flex flex-wrap items-center gap-3">
				<button
					type="button"
					class="btn btn-primary text-sm"
					disabled={!draftMapConfig}
					onclick={applyDraftMapBounds}
				>
					{$messages.editor.mapApplyCurrentView}
				</button>
				{#if draftMapConfig}
					<p class="text-sm font-semibold text-sky-700">{$messages.editor.mapCurrentViewUnsaved}</p>
				{:else}
					<p class="editor-text-muted text-sm">{$messages.editor.mapCurrentViewSaved}</p>
				{/if}
			</div>
			<MapPointEditor
				mode="author"
				{mapConfig}
				baseLayer={previewPlayerBaseLayer ? (mapConfig.base_layer ?? 'osm') : 'osm'}
				correctPoint={mapAnswer.correct_point}
				selectionBounds={mapConfig.bounds}
				scoringAnswer={mapAnswer}
				heightClass="aspect-[4/3] min-h-[24rem]"
				onPointChange={setCorrectMapPoint}
				onViewportChange={(config) => (draftMapConfig = config)}
				onBoundsChange={(config) => {
					step.player_input.map = config;
					draftMapConfig = null;
				}}
				onScoringAnswerChange={setMapAnswer}
			/>
		</div>

		<div
			class={`grid gap-3 ${mapAnswer.scoring_mode === 'linear' ? 'md:grid-cols-4' : 'md:grid-cols-2'}`}
		>
			<label class="input-wrap">
				<span class="editor-text-muted text-sm font-bold uppercase tracking-wide">
					{$messages.editor.mapScoringMode}
				</span>
				<select
					class="input text-lg"
					value={mapAnswer.scoring_mode}
					onchange={(event) =>
						setMapScoringMode(
							(event.currentTarget as HTMLSelectElement).value as MapDistanceAnswer['scoring_mode']
						)}
				>
					<option value="bands">{$messages.editor.mapScoringBands}</option>
					<option value="linear">{$messages.editor.mapScoringLinear}</option>
				</select>
			</label>
			<label class="input-wrap">
				<span class="editor-text-muted text-sm font-bold uppercase tracking-wide">
					{$messages.editor.mapMaxPoints}
				</span>
				<input
					class="input text-lg"
					type="number"
					min="0"
					value={mapAnswer.max_points}
					oninput={(event) =>
						updateMapAnswer({
							max_points: Math.max(
								0,
								Math.trunc(Number((event.currentTarget as HTMLInputElement).value) || 0)
							)
						})}
				/>
			</label>
			{#if mapAnswer.scoring_mode === 'linear'}
				<label class="input-wrap">
					<span class="editor-text-muted text-sm font-bold uppercase tracking-wide">
						{$messages.editor.mapFullCreditDistance}
					</span>
					<input
						class="input text-lg"
						type="number"
						min="0"
						value={mapAnswer.full_credit_distance_m ?? 0}
						oninput={(event) =>
							updateMapAnswer({
								full_credit_distance_m: Math.max(
									0,
									Number((event.currentTarget as HTMLInputElement).value) || 0
								)
							})}
					/>
				</label>
				<label class="input-wrap">
					<span class="editor-text-muted text-sm font-bold uppercase tracking-wide">
						{$messages.editor.mapZeroDistance}
					</span>
					<input
						class="input text-lg"
						type="number"
						min="1"
						value={mapAnswer.zero_distance_m ?? 50_000}
						oninput={(event) =>
							updateMapAnswer({
								zero_distance_m: Math.max(
									1,
									Number((event.currentTarget as HTMLInputElement).value) || 1
								)
							})}
					/>
				</label>
			{/if}
		</div>

		<div class="flex flex-wrap gap-2">
			<button
				type="button"
				class="btn btn-ghost text-sm"
				onclick={() => applyMapScoringPreset('street')}
			>
				{$messages.editor.mapStreetPreset}
			</button>
			<button
				type="button"
				class="btn btn-ghost text-sm"
				onclick={() => applyMapScoringPreset('city')}
			>
				{$messages.editor.mapCityPreset}
			</button>
			<button
				type="button"
				class="btn btn-ghost text-sm"
				onclick={() => applyMapScoringPreset('country')}
			>
				{$messages.editor.mapCountryPreset}
			</button>
		</div>

		{#if mapAnswer.scoring_mode === 'bands'}
			<div class="grid gap-3">
				<div class="flex items-center justify-between gap-3">
					<p class="editor-text-muted text-sm font-bold uppercase tracking-wide">
						{$messages.editor.mapBands}
					</p>
					<button type="button" class="btn btn-ghost text-sm" onclick={addMapBand}>
						{$messages.editor.addMapBand}
					</button>
				</div>
				{#each mapAnswer.bands ?? [] as band, index}
					<div class="grid gap-2 md:grid-cols-[minmax(0,1fr)_9rem_8rem_8rem]">
						<input
							class="input"
							value={band.label ?? ''}
							placeholder={$messages.editor.mapBandLabel}
							oninput={(event) =>
								updateMapBand(index, {
									label: (event.currentTarget as HTMLInputElement).value
								})}
						/>
						<input
							class="input"
							type="number"
							min="0"
							value={band.distance_m}
							placeholder={$messages.editor.mapBandDistance}
							oninput={(event) =>
								updateMapBand(index, {
									distance_m: Math.max(
										0,
										Number((event.currentTarget as HTMLInputElement).value) || 0
									)
								})}
						/>
						<input
							class="input"
							type="number"
							min="0"
							value={band.points}
							placeholder={$messages.editor.points}
							oninput={(event) =>
								updateMapBand(index, {
									points: Math.max(
										0,
										Math.trunc(Number((event.currentTarget as HTMLInputElement).value) || 0)
									)
								})}
						/>
						<button
							type="button"
							class="btn btn-ghost text-sm"
							disabled={(mapAnswer.bands ?? []).length <= 1}
							onclick={() => removeMapBand(index)}
						>
							{$messages.editor.removeMapBand}
						</button>
					</div>
				{/each}
			</div>
		{/if}
	</div>
{:else if step.evaluation.type_ === 'exact_text' && step.player_input.kind === 'radio'}
	<div class="editor-nested-panel editor-text-muted rounded-2xl border p-4 text-sm">
		<p class="editor-text font-bold">{$messages.editor.markCorrectOption}</p>
		<p class="mt-2">{$messages.editor.markCorrectOptionHelp}</p>
	</div>
{:else if step.evaluation.type_ === 'exact_text' && step.player_input.kind === 'text'}
	<div class="grid gap-3">
		<div class="grid gap-3">
			<div class="flex items-center justify-between gap-3">
				<p class="editor-text-muted text-sm font-bold uppercase tracking-wide">
					{$messages.editor.acceptedAnswers}
				</p>
				<button type="button" class="btn btn-ghost text-sm" onclick={addTextAnswer}>
					{$messages.editor.addAcceptedAnswer}
				</button>
			</div>
			{#each textAnswers as answer, index}
				<div class="grid gap-2 md:grid-cols-[minmax(0,1fr)_8rem]">
					<input
						class="input text-lg"
						value={answer}
						placeholder={$messages.editor.expectedAnswerPlaceholder}
						oninput={(event) =>
							setTextAnswer(index, (event.currentTarget as HTMLInputElement).value)}
					/>
					<button
						type="button"
						class="btn btn-ghost text-sm"
						disabled={textAnswers.length <= 1}
						onclick={() => removeTextAnswer(index)}
					>
						{$messages.editor.removeAcceptedAnswer}
					</button>
				</div>
			{/each}
		</div>
		<label class="input-wrap md:max-w-xs">
			<span class="editor-text-muted text-sm font-bold uppercase tracking-wide">
				{$messages.editor.typoTolerance}
			</span>
			<input
				class="input text-lg"
				type="number"
				min="0"
				step="1"
				value={getExactTextMaxDistance(step)}
				oninput={(event) =>
					(step.evaluation.max_distance = Math.max(
						0,
						Math.trunc(Number((event.currentTarget as HTMLInputElement).value) || 0)
					))}
			/>
			<span class="editor-text-muted text-sm">{$messages.editor.typoToleranceHelp}</span>
		</label>
	</div>
{:else if step.evaluation.type_ === 'host_judged'}
	<div class="grid gap-3">
		<div class="editor-nested-panel editor-text-muted rounded-2xl border p-4 text-sm">
			<p class="editor-text font-bold">{$messages.editor.hostDecidesCorrectness}</p>
			<p class="mt-2">{$messages.editor.hostReviewedHelp}</p>
		</div>
		<label class="input-wrap">
			<span class="editor-text-muted text-sm font-bold uppercase tracking-wide">
				{$messages.editor.correctAnswerRubric}
			</span>
			<input
				class="input text-lg"
				value={getTextAnswer(step)}
				placeholder={$messages.editor.expectedAnswerPlaceholder}
				oninput={(event) =>
					(step.evaluation.answer = (event.currentTarget as HTMLInputElement).value)}
			/>
		</label>
	</div>
{:else if step.evaluation.type_ !== 'none'}
	<label class="input-wrap">
		<span class="editor-text-muted text-sm font-bold uppercase tracking-wide">
			{$messages.editor.correctAnswerRubric}
		</span>
		<input
			class="input text-lg"
			value={getTextAnswer(step)}
			placeholder={$messages.editor.expectedAnswerPlaceholder}
			oninput={(event) =>
				(step.evaluation.answer = (event.currentTarget as HTMLInputElement).value)}
		/>
	</label>
{:else}
	<div class="editor-nested-panel editor-text-muted rounded-2xl border p-4 text-sm">
		<p class="editor-text font-bold">{$messages.editor.noAnswerRequired}</p>
		<p class="mt-2">{$messages.editor.displayOnlyHelp}</p>
	</div>
{/if}
