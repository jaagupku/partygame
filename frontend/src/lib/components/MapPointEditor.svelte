<script lang="ts">
	import 'leaflet/dist/leaflet.css';
	import { browser } from '$app/environment';
	import { onDestroy, onMount, tick } from 'svelte';
	import { DEFAULT_AVATAR_PRESET_KEY, getAvatarSrc } from '$lib/avatar-presets';
	import {
		clampMapPointToBounds,
		DEFAULT_MAP_CONFIG
	} from '$lib/components/definition-editor/helpers';
	import { getMapTileLayerDefinition } from '$lib/map-layers';
	import { buildMapRevealFitTarget, revealFitKey } from '$lib/map-reveal-fit';

	type LeafletModule = typeof import('leaflet');
	type MapEditorMode = 'author' | 'player' | 'reveal' | 'custom';
	type GuessLabelMode = 'hover' | 'always' | 'none';

	export type MapGuessMarker = {
		id: string;
		name: string;
		point: MapPoint;
		avatarKind?: 'preset' | 'custom' | null;
		avatarPresetKey?: string | null;
		avatarUrl?: string | null;
	};

	type Props = {
		mode?: MapEditorMode;
		mapConfig?: MapInputConfig;
		selectedPoint?: MapPoint | null;
		correctPoint?: MapPoint | null;
		guessMarkers?: MapGuessMarker[];
		editablePoint?: boolean;
		editableViewport?: boolean;
		showCorrect?: boolean;
		showGuesses?: boolean;
		showLines?: boolean;
		showBounds?: boolean;
		editableBounds?: boolean;
		scoringAnswer?: MapDistanceAnswer | null;
		editableScoring?: boolean;
		fitRevealToGuesses?: boolean;
		editingWorldView?: boolean;
		guessLabelMode?: GuessLabelMode;
		selectionBounds?: MapBounds;
		baseLayer?: MapInputConfig['base_layer'];
		heightClass?: string;
		resetViewKey?: string | number | null;
		lockViewToBounds?: boolean;
		onPointChange?: (point: MapPoint) => void;
		onMapConfigChange?: (config: MapInputConfig) => void;
		onViewportChange?: (config: MapInputConfig) => void;
		onBoundsChange?: (config: MapInputConfig) => void;
		onScoringAnswerChange?: (answer: MapDistanceAnswer) => void;
	};

	let {
		mode = 'custom',
		mapConfig = DEFAULT_MAP_CONFIG,
		selectedPoint = null,
		correctPoint = null,
		guessMarkers = [],
		editablePoint = undefined,
		editableViewport = undefined,
		showCorrect = undefined,
		showGuesses = undefined,
		showLines = undefined,
		showBounds = undefined,
		editableBounds = undefined,
		scoringAnswer = null,
		editableScoring = undefined,
		fitRevealToGuesses = undefined,
		editingWorldView = undefined,
		guessLabelMode = undefined,
		selectionBounds = undefined,
		baseLayer = undefined,
		heightClass = 'h-80',
		resetViewKey = undefined,
		lockViewToBounds = undefined,
		onPointChange,
		onMapConfigChange,
		onViewportChange,
		onBoundsChange,
		onScoringAnswerChange
	}: Props = $props();

	let container: HTMLDivElement;
	let leaflet: LeafletModule | null = null;
	let map: import('leaflet').Map | null = null;
	let selectedMarker: import('leaflet').Marker | null = null;
	let correctMarker: import('leaflet').Marker | null = null;
	let guessLayer: import('leaflet').LayerGroup | null = null;
	let lineLayer: import('leaflet').LayerGroup | null = null;
	let boundsLayer: import('leaflet').LayerGroup | null = null;
	let scoringLayer: import('leaflet').LayerGroup | null = null;
	let tileLayer: import('leaflet').TileLayer | null = null;
	let activeBaseLayer: MapInputConfig['base_layer'] | undefined = undefined;
	let lastRevealFitKey = '';
	let lastResetViewKey: string | number | null | undefined = undefined;

	const displayedBaseLayer = $derived(baseLayer ?? mapConfig.base_layer ?? 'osm');
	const selectionLimitBounds = $derived(selectionBounds ?? mapConfig.bounds);
	const effectiveEditablePoint = $derived(
		editablePoint ?? (mode === 'author' || mode === 'player')
	);
	const effectiveEditableViewport = $derived(editableViewport ?? mode === 'author');
	const effectiveShowCorrect = $derived(showCorrect ?? (mode === 'author' || mode === 'reveal'));
	const effectiveShowGuesses = $derived(showGuesses ?? mode === 'reveal');
	const effectiveShowLines = $derived(showLines ?? mode === 'reveal');
	const effectiveShowBounds = $derived(showBounds ?? true);
	const effectiveEditableBounds = $derived(editableBounds ?? mode === 'author');
	const effectiveEditableScoring = $derived(editableScoring ?? mode === 'author');
	const effectiveFitRevealToGuesses = $derived(fitRevealToGuesses ?? mode === 'reveal');
	const effectiveEditingWorldView = $derived(editingWorldView ?? mode === 'author');
	const effectiveLockViewToBounds = $derived(lockViewToBounds ?? mode === 'player');
	const effectiveGuessLabelMode = $derived(
		guessLabelMode ?? (mode === 'reveal' ? 'hover' : 'always')
	);

	const mapBoundsTuple = $derived.by(
		() =>
			[
				[mapConfig.bounds.south, mapConfig.bounds.west],
				[mapConfig.bounds.north, mapConfig.bounds.east]
			] as [[number, number], [number, number]]
	);

	onMount(async () => {
		if (!browser) {
			return;
		}
		leaflet = await import('leaflet');
		await tick();
		if (!container || !leaflet) {
			return;
		}
		map = leaflet.map(container, {
			center: [mapConfig.initial_center.lat, mapConfig.initial_center.lng],
			zoom: mapConfig.initial_zoom,
			minZoom: effectiveEditingWorldView ? 2 : mapConfig.min_zoom,
			maxZoom: mapConfig.max_zoom,
			maxBounds: effectiveEditableViewport ? undefined : mapBoundsTuple,
			maxBoundsViscosity: effectiveEditableViewport ? 0 : 1,
			attributionControl: true,
			zoomControl: true
		});
		syncBaseLayer();
		guessLayer = leaflet.layerGroup().addTo(map);
		lineLayer = leaflet.layerGroup().addTo(map);
		boundsLayer = leaflet.layerGroup().addTo(map);
		scoringLayer = leaflet.layerGroup().addTo(map);
		map.on('click', (event) => {
			if (!effectiveEditablePoint || !map) {
				return;
			}
			const point = clampMapPointToBounds(
				{ lat: event.latlng.lat, lng: event.latlng.lng },
				selectionLimitBounds
			);
			onPointChange?.(point);
		});
		map.on('moveend zoomend', () => {
			if (!effectiveEditableViewport || !map) {
				return;
			}
			const bounds = map.getBounds();
			const center = map.getCenter();
			const nextConfig: MapInputConfig = {
				selection_mode: 'point',
				bounds: {
					north: roundCoord(bounds.getNorth()),
					south: roundCoord(bounds.getSouth()),
					east: roundCoord(bounds.getEast()),
					west: roundCoord(bounds.getWest())
				},
				base_layer: mapConfig.base_layer,
				initial_center: {
					lat: roundCoord(center.lat),
					lng: roundCoord(center.lng)
				},
				initial_zoom: map.getZoom(),
				min_zoom: effectiveEditingWorldView
					? Math.min(mapConfig.min_zoom ?? 2, 2)
					: mapConfig.min_zoom,
				max_zoom: mapConfig.max_zoom
			};
			onViewportChange?.(nextConfig);
			onMapConfigChange?.(nextConfig);
		});
		syncMap();
	});

	onDestroy(() => {
		map?.remove();
		map = null;
	});

	$effect(() => {
		JSON.stringify(mapConfig);
		JSON.stringify(selectionLimitBounds);
		JSON.stringify(selectedPoint);
		JSON.stringify(correctPoint);
		JSON.stringify(guessMarkers);
		JSON.stringify(scoringAnswer);
		mode;
		displayedBaseLayer;
		effectiveEditablePoint;
		effectiveEditableViewport;
		effectiveEditableScoring;
		effectiveFitRevealToGuesses;
		effectiveEditingWorldView;
		effectiveLockViewToBounds;
		effectiveShowCorrect;
		effectiveShowGuesses;
		effectiveShowLines;
		effectiveShowBounds;
		effectiveEditableBounds;
		effectiveGuessLabelMode;
		resetViewKey;
		syncMap();
	});

	function syncMap() {
		if (!map || !leaflet) {
			return;
		}
		if (!effectiveEditableViewport) {
			map.setMaxBounds(mapBoundsTuple);
			if (mapConfig.min_zoom !== undefined) {
				map.setMinZoom(mapConfig.min_zoom);
			}
			if (mapConfig.max_zoom !== undefined) {
				map.setMaxZoom(mapConfig.max_zoom);
			}
		}
		syncBaseLayer();
		syncPointMarker();
		syncCorrectMarker();
		syncGuessMarkers();
		syncBounds();
		syncScoringCircles();
		window.setTimeout(() => {
			map?.invalidateSize();
			syncViewConstraints();
			resetViewToBounds();
			fitRevealBounds();
		}, 0);
	}

	function syncViewConstraints() {
		if (!map || !leaflet || effectiveEditableViewport) {
			return;
		}
		map.setMaxBounds(mapBoundsTuple);
		if (mapConfig.max_zoom !== undefined) {
			map.setMaxZoom(mapConfig.max_zoom);
		}
		const nextMinZoom = effectiveMinZoom();
		if (nextMinZoom !== undefined) {
			map.setMinZoom(nextMinZoom);
		}
		map.panInsideBounds(mapBoundsTuple, { animate: false });
	}

	function effectiveMinZoom() {
		const configuredMinZoom = mapConfig.min_zoom;
		if (!map || !effectiveLockViewToBounds) {
			return configuredMinZoom;
		}
		const lockedMinZoom = map.getBoundsZoom(mapBoundsTuple, true);
		if (!Number.isFinite(lockedMinZoom)) {
			return configuredMinZoom;
		}
		const nextMinZoom = Math.max(configuredMinZoom ?? lockedMinZoom, lockedMinZoom);
		return mapConfig.max_zoom === undefined
			? nextMinZoom
			: Math.min(mapConfig.max_zoom, nextMinZoom);
	}

	function syncBaseLayer() {
		if (!map || !leaflet || activeBaseLayer === displayedBaseLayer) {
			return;
		}
		tileLayer?.remove();
		const definition = getMapTileLayerDefinition(displayedBaseLayer);
		tileLayer = leaflet.tileLayer(definition.url, {
			maxZoom: definition.maxZoom,
			attribution: definition.attribution
		});
		tileLayer.addTo(map);
		activeBaseLayer = displayedBaseLayer;
	}

	function syncPointMarker() {
		if (!map || !leaflet) {
			return;
		}
		if (!selectedPoint) {
			selectedMarker?.remove();
			selectedMarker = null;
			return;
		}
		const latLng: [number, number] = [selectedPoint.lat, selectedPoint.lng];
		if (!selectedMarker) {
			selectedMarker = leaflet.marker(latLng, { icon: pointIcon('selected') }).addTo(map);
			return;
		}
		selectedMarker.setLatLng(latLng);
	}

	function syncCorrectMarker() {
		if (!map || !leaflet) {
			return;
		}
		if (!effectiveShowCorrect || !correctPoint) {
			correctMarker?.remove();
			correctMarker = null;
			return;
		}
		const latLng: [number, number] = [correctPoint.lat, correctPoint.lng];
		if (!correctMarker) {
			correctMarker = leaflet.marker(latLng, { icon: pointIcon('correct') }).addTo(map);
			return;
		}
		correctMarker.setLatLng(latLng);
	}

	function syncGuessMarkers() {
		if (!map || !leaflet || !guessLayer || !lineLayer) {
			return;
		}
		guessLayer.clearLayers();
		lineLayer.clearLayers();
		if (!effectiveShowGuesses) {
			return;
		}
		for (const marker of guessMarkers) {
			const guessMarker = leaflet
				.marker([marker.point.lat, marker.point.lng], { icon: guessIcon(marker) })
				.addTo(guessLayer);
			if (correctPoint && effectiveGuessLabelMode !== 'none') {
				guessMarker.bindTooltip(`${marker.name}: ${formatDistance(marker.point, correctPoint)}`, {
					direction: 'top',
					offset: [0, -26],
					opacity: 0.92,
					permanent: effectiveGuessLabelMode === 'always'
				});
			}
			if (effectiveShowLines && correctPoint) {
				leaflet
					.polyline(
						[
							[marker.point.lat, marker.point.lng],
							[correctPoint.lat, correctPoint.lng]
						],
						{
							color: '#0f172a',
							opacity: 0.22,
							weight: 2,
							dashArray: '5 7'
						}
					)
					.addTo(lineLayer);
			}
		}
	}

	function syncBounds() {
		if (!map || !leaflet || !boundsLayer) {
			return;
		}
		boundsLayer.clearLayers();
		if (!effectiveShowBounds) {
			return;
		}
		const rectangle = leaflet
			.rectangle(mapBoundsTuple, {
				color: '#0284c7',
				weight: 2,
				opacity: 0.8,
				fill: false,
				dashArray: '8 6'
			})
			.addTo(boundsLayer);
		if (!effectiveEditableBounds) {
			return;
		}
		for (const handle of boundsHandles(mapConfig.bounds)) {
			const marker = leaflet
				.marker([handle.point.lat, handle.point.lng], {
					draggable: true,
					icon: boundsHandleIcon(handle.cursor)
				})
				.addTo(boundsLayer)
				.bindTooltip(handle.label, { direction: 'top', offset: [0, -12] });
			marker.on('drag', () => {
				rectangle.setBounds(boundsToTuple(boundsFromHandle(handle.kind, marker.getLatLng())));
			});
			marker.on('dragend', () => {
				commitBounds(boundsFromHandle(handle.kind, marker.getLatLng()));
			});
		}
	}

	function syncScoringCircles() {
		if (!map || !leaflet || !scoringLayer || !scoringAnswer?.correct_point) {
			scoringLayer?.clearLayers();
			return;
		}
		scoringLayer.clearLayers();
		const center = scoringAnswer.correct_point;
		const radii = scoringRadii(scoringAnswer);
		for (const radius of radii) {
			const circle = leaflet
				.circle([center.lat, center.lng], {
					radius: radius.distance_m,
					color: radius.color,
					weight: 2,
					opacity: 0.82,
					fillColor: radius.color,
					fillOpacity: 0.05
				})
				.addTo(scoringLayer)
				.bindTooltip(radius.label, { sticky: true });
			if (effectiveEditableScoring) {
				const handlePoint = pointAtDistanceEast(center, radius.distance_m);
				const handle = leaflet
					.marker([handlePoint.lat, handlePoint.lng], {
						draggable: true,
						icon: radiusHandleIcon(radius.color)
					})
					.addTo(scoringLayer)
					.bindTooltip(radius.label, { direction: 'right', offset: [12, 0] });
				handle.on('drag', () => {
					circle.setRadius(distanceFromHandle(center, handle));
				});
				handle.on('dragend', () => {
					const distance = distanceFromHandle(center, handle);
					updateScoringRadius(radius.kind, radius.index, distance);
				});
			}
		}
	}

	function fitRevealBounds() {
		if (!map || !leaflet || !effectiveFitRevealToGuesses || !effectiveShowGuesses) {
			lastRevealFitKey = '';
			return;
		}
		const target = buildMapRevealFitTarget(guessMarkers, correctPoint, {
			includeCorrect: effectiveShowCorrect,
			maxZoom: mapConfig.max_zoom,
			padding: [72, 72]
		});
		if (!target) {
			lastRevealFitKey = '';
			return;
		}
		const fitKey =
			target.kind === 'point' ? revealFitKey([target.point]) : revealFitKey(target.points);
		if (fitKey === lastRevealFitKey) {
			return;
		}
		lastRevealFitKey = fitKey;
		if (target.kind === 'point') {
			map.flyTo([target.point.lat, target.point.lng], target.zoom, {
				animate: true,
				duration: 1.15
			});
			return;
		}
		const bounds = leaflet.latLngBounds(target.points.map((point) => [point.lat, point.lng]));
		map.flyToBounds(bounds, {
			animate: true,
			duration: 1.15,
			padding: target.padding,
			maxZoom: target.maxZoom
		});
	}

	function resetViewToBounds() {
		if (!map || !leaflet || resetViewKey === undefined || resetViewKey === null) {
			return;
		}
		if (resetViewKey === lastResetViewKey) {
			return;
		}
		lastResetViewKey = resetViewKey;
		map.fitBounds(mapBoundsTuple, {
			animate: false,
			padding: [12, 12],
			maxZoom: mapConfig.max_zoom
		});
	}

	function scoringRadii(answer: MapDistanceAnswer) {
		const radii: Array<{
			kind: 'full' | 'zero' | 'band';
			index: number;
			distance_m: number;
			label: string;
			color: string;
		}> = [];
		if (answer.scoring_mode === 'linear' && answer.full_credit_distance_m != null) {
			radii.push({
				kind: 'full',
				index: -1,
				distance_m: answer.full_credit_distance_m,
				label: `Full credit: ${formatDistanceMeters(answer.full_credit_distance_m)}`,
				color: '#10b981'
			});
		}
		if (answer.scoring_mode === 'bands') {
			for (const [index, band] of (answer.bands ?? []).entries()) {
				radii.push({
					kind: 'band',
					index,
					distance_m: band.distance_m,
					label: `${band.label || `Band ${index + 1}`}: ${formatDistanceMeters(band.distance_m)} / ${band.points} pts`,
					color: '#f59e0b'
				});
			}
		}
		if (answer.scoring_mode === 'linear' && answer.zero_distance_m != null) {
			radii.push({
				kind: 'zero',
				index: -1,
				distance_m: answer.zero_distance_m,
				label: `Zero points: ${formatDistanceMeters(answer.zero_distance_m)}`,
				color: '#ef4444'
			});
		}
		return radii.filter((radius) => radius.distance_m > 0);
	}

	function updateScoringRadius(kind: 'full' | 'zero' | 'band', index: number, distance: number) {
		if (!scoringAnswer || !onScoringAnswerChange) {
			return;
		}
		const nextDistance = Math.max(1, distance);
		if (kind === 'full') {
			const zeroDistance = scoringAnswer.zero_distance_m ?? nextDistance;
			onScoringAnswerChange({
				...scoringAnswer,
				full_credit_distance_m: Math.min(nextDistance, zeroDistance)
			});
			return;
		}
		if (kind === 'zero') {
			onScoringAnswerChange({
				...scoringAnswer,
				zero_distance_m: Math.max(nextDistance, scoringAnswer.full_credit_distance_m ?? 1)
			});
			return;
		}
		const bands = [...(scoringAnswer.bands ?? [])];
		if (!bands[index]) {
			return;
		}
		bands[index] = { ...bands[index], distance_m: nextDistance };
		onScoringAnswerChange({ ...scoringAnswer, bands });
	}

	function boundsHandles(bounds: MapBounds) {
		return [
			{
				kind: 'northwest' as const,
				label: 'Resize area',
				cursor: 'nwse-resize',
				point: { lat: bounds.north, lng: bounds.west }
			},
			{
				kind: 'northeast' as const,
				label: 'Resize area',
				cursor: 'nesw-resize',
				point: { lat: bounds.north, lng: bounds.east }
			},
			{
				kind: 'southeast' as const,
				label: 'Resize area',
				cursor: 'nwse-resize',
				point: { lat: bounds.south, lng: bounds.east }
			},
			{
				kind: 'southwest' as const,
				label: 'Resize area',
				cursor: 'nesw-resize',
				point: { lat: bounds.south, lng: bounds.west }
			},
			{
				kind: 'move' as const,
				label: 'Move area',
				cursor: 'move',
				point: {
					lat: (bounds.north + bounds.south) / 2,
					lng: (bounds.east + bounds.west) / 2
				}
			}
		];
	}

	function boundsFromHandle(
		kind: 'northwest' | 'northeast' | 'southeast' | 'southwest' | 'move',
		latLng: import('leaflet').LatLng
	): MapBounds {
		const next = { ...mapConfig.bounds };
		const lat = clamp(latLng.lat, -85, 85);
		const lng = clamp(latLng.lng, -180, 180);
		if (kind === 'move') {
			const height = next.north - next.south;
			const width = next.east - next.west;
			const halfHeight = height / 2;
			const halfWidth = width / 2;
			const centerLat = clamp(lat, -85 + halfHeight, 85 - halfHeight);
			const centerLng = clamp(lng, -180 + halfWidth, 180 - halfWidth);
			return {
				north: roundCoord(centerLat + halfHeight),
				south: roundCoord(centerLat - halfHeight),
				east: roundCoord(centerLng + halfWidth),
				west: roundCoord(centerLng - halfWidth)
			};
		}
		if (kind.includes('north')) {
			next.north = Math.max(lat, next.south + 0.0001);
		} else {
			next.south = Math.min(lat, next.north - 0.0001);
		}
		if (kind.includes('east')) {
			next.east = Math.max(lng, next.west + 0.0001);
		} else {
			next.west = Math.min(lng, next.east - 0.0001);
		}
		return {
			north: roundCoord(next.north),
			south: roundCoord(next.south),
			east: roundCoord(next.east),
			west: roundCoord(next.west)
		};
	}

	function commitBounds(bounds: MapBounds) {
		const center = {
			lat: roundCoord((bounds.north + bounds.south) / 2),
			lng: roundCoord((bounds.east + bounds.west) / 2)
		};
		const nextConfig = {
			...mapConfig,
			bounds,
			initial_center: center,
			initial_zoom: map?.getZoom() ?? mapConfig.initial_zoom
		};
		onBoundsChange?.(nextConfig);
		onMapConfigChange?.(nextConfig);
	}

	function boundsToTuple(bounds: MapBounds): [[number, number], [number, number]] {
		return [
			[bounds.south, bounds.west],
			[bounds.north, bounds.east]
		];
	}

	function clamp(value: number, min: number, max: number) {
		return Math.min(max, Math.max(min, value));
	}

	function distanceFromHandle(center: MapPoint, handle: import('leaflet').Marker) {
		const latLng = handle.getLatLng();
		return Math.round(distanceMeters(center, { lat: latLng.lat, lng: latLng.lng }));
	}

	function pointIcon(kind: 'selected' | 'correct') {
		return leaflet?.divIcon({
			className: '',
			html: `<span class="map-point-marker map-point-marker-${kind}"></span>`,
			iconSize: [30, 30],
			iconAnchor: [15, 15]
		});
	}

	function guessIcon(marker: MapGuessMarker) {
		const avatarSrc = getAvatarSrc(
			marker.avatarKind ?? 'preset',
			marker.avatarPresetKey ?? DEFAULT_AVATAR_PRESET_KEY,
			marker.avatarUrl ?? null
		);
		const image = avatarSrc
			? `<img class="map-guess-marker-image" src="${escapeHtml(avatarSrc)}" alt="" />`
			: `<span>${initials(marker.name)}</span>`;
		return leaflet?.divIcon({
			className: '',
			html: `<span class="map-guess-marker" title="${escapeHtml(marker.name)}">${image}</span>`,
			iconSize: [44, 44],
			iconAnchor: [22, 22]
		});
	}

	function radiusHandleIcon(color: string) {
		return leaflet?.divIcon({
			className: '',
			html: `<span class="map-radius-handle" style="--handle-color: ${color}"></span>`,
			iconSize: [22, 22],
			iconAnchor: [11, 11]
		});
	}

	function boundsHandleIcon(cursor: string) {
		return leaflet?.divIcon({
			className: '',
			html: `<span class="map-bounds-handle" style="--handle-cursor: ${cursor}"></span>`,
			iconSize: [18, 18],
			iconAnchor: [9, 9]
		});
	}

	function initials(name: string) {
		return escapeHtml(
			name
				.trim()
				.split(/\s+/)
				.slice(0, 2)
				.map((part) => part[0]?.toUpperCase() ?? '')
				.join('') || '?'
		);
	}

	function escapeHtml(value: string) {
		return value
			.replaceAll('&', '&amp;')
			.replaceAll('<', '&lt;')
			.replaceAll('>', '&gt;')
			.replaceAll('"', '&quot;');
	}

	function roundCoord(value: number) {
		return Number(value.toFixed(6));
	}

	function formatDistance(left: MapPoint, right: MapPoint) {
		return formatDistanceMeters(distanceMeters(left, right));
	}

	function formatDistanceMeters(distance: number) {
		return distance >= 1000 ? `${(distance / 1000).toFixed(1)} km` : `${Math.round(distance)} m`;
	}

	function distanceMeters(left: MapPoint, right: MapPoint) {
		const earthRadiusM = 6371000;
		const leftLat = toRadians(left.lat);
		const rightLat = toRadians(right.lat);
		const deltaLat = toRadians(right.lat - left.lat);
		const deltaLng = toRadians(right.lng - left.lng);
		const halfChord =
			Math.sin(deltaLat / 2) ** 2 +
			Math.cos(leftLat) * Math.cos(rightLat) * Math.sin(deltaLng / 2) ** 2;
		return 2 * earthRadiusM * Math.asin(Math.sqrt(halfChord));
	}

	function pointAtDistanceEast(point: MapPoint, distanceM: number): MapPoint {
		const metersPerLng = 111320 * Math.cos(toRadians(point.lat));
		return {
			lat: point.lat,
			lng: point.lng + distanceM / Math.max(1, metersPerLng)
		};
	}

	function toRadians(value: number) {
		return (value * Math.PI) / 180;
	}
</script>

<div class={`map-shell ${heightClass}`} bind:this={container}></div>

<style>
	.map-shell {
		width: 100%;
		min-height: 16rem;
		overflow: hidden;
		border: 1px solid rgb(203 213 225);
		border-radius: 0.75rem;
		background: rgb(226 232 240);
	}

	:global(.map-point-marker) {
		display: block;
		width: 1.875rem;
		height: 1.875rem;
		border: 4px solid white;
		border-radius: 999px;
		box-shadow: 0 10px 22px rgb(15 23 42 / 0.28);
	}

	:global(.map-point-marker-selected) {
		background: rgb(14 165 233);
	}

	:global(.map-point-marker-correct) {
		background: rgb(16 185 129);
		box-shadow:
			0 0 0 0.5rem rgb(16 185 129 / 0.18),
			0 12px 26px rgb(15 23 42 / 0.3);
	}

	:global(.map-guess-marker) {
		display: grid;
		width: 2.75rem;
		height: 2.75rem;
		place-items: center;
		overflow: hidden;
		border: 3px solid white;
		border-radius: 999px;
		background:
			radial-gradient(circle at top, rgb(255 255 255 / 0.9), rgb(255 255 255 / 0.4)),
			linear-gradient(135deg, #dbeafe, #fef3c7);
		color: #0f172a;
		font-size: 0.8rem;
		font-weight: 900;
		box-shadow:
			0 0 0 0.25rem rgb(37 99 235 / 0.22),
			0 12px 24px rgb(15 23 42 / 0.24);
	}

	:global(.leaflet-container .map-guess-marker-image) {
		display: block;
		width: 100% !important;
		height: 100% !important;
		max-width: 100% !important;
		max-height: 100% !important;
		object-fit: cover;
	}

	:global(.map-radius-handle) {
		display: block;
		width: 1.375rem;
		height: 1.375rem;
		border: 3px solid white;
		border-radius: 999px;
		background: var(--handle-color);
		box-shadow: 0 8px 18px rgb(15 23 42 / 0.24);
		cursor: grab;
	}

	:global(.map-bounds-handle) {
		display: block;
		width: 1.125rem;
		height: 1.125rem;
		border: 3px solid white;
		border-radius: 999px;
		background: #0284c7;
		box-shadow:
			0 0 0 0.25rem rgb(2 132 199 / 0.2),
			0 8px 18px rgb(15 23 42 / 0.24);
		cursor: var(--handle-cursor);
	}
</style>
