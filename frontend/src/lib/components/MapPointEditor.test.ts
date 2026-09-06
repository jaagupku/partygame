import { cleanup, render } from '@testing-library/svelte';
import { tick } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MapPointEditor from './MapPointEditor.svelte';
import StepDisplayPreview from './StepDisplayPreview.svelte';
import { createOpenFreeMapLayer } from '$lib/openfreemap-layer';
import { DEFAULT_MAP_CONFIG } from './definition-editor/helpers';

vi.hoisted(() => {
	window.matchMedia = vi
		.fn()
		.mockReturnValue({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() });
});

vi.mock('$app/environment', () => ({ browser: true }));

vi.mock('$lib/openfreemap-layer', async () => {
	const leaflet = await import('leaflet');
	return {
		createOpenFreeMapLayer: vi.fn(() => {
			const layer = new leaflet.Layer();
			layer.onAdd = vi.fn(() => layer);
			layer.onRemove = vi.fn(() => layer);
			return layer;
		})
	};
});

let restoreLeafletBrowser: () => void;

beforeEach(async () => {
	vi.clearAllMocks();
	vi.useFakeTimers();
	vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get').mockReturnValue(1000);
	vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(600);
	const leaflet = await import('leaflet');
	const descriptors = Object.getOwnPropertyDescriptors(leaflet.Browser);
	// Enable real SVG rendering and flyTo animation in jsdom.
	Object.defineProperties(leaflet.Browser, {
		svg: { ...descriptors.svg, value: true },
		any3d: { ...descriptors.any3d, value: true }
	});
	restoreLeafletBrowser = () => Object.defineProperties(leaflet.Browser, descriptors);
});

afterEach(() => {
	cleanup();
	restoreLeafletBrowser();
	vi.useRealTimers();
	vi.restoreAllMocks();
});

describe('map reveal lifecycle', () => {
	it.each([
		DEFAULT_MAP_CONFIG,
		{
			...DEFAULT_MAP_CONFIG,
			bounds: { north: 59.5, south: 59.3, east: 24.9, west: 24.5 },
			initial_center: { lat: 59.4, lng: 24.7 },
			initial_zoom: 12
		}
	])('settles after revealing scoring circles and guesses ($initial_zoom)', async (mapConfig) => {
		const leaflet = await import('leaflet');
		const fly = vi.spyOn(leaflet.Map.prototype, 'flyTo');
		const move = vi.spyOn(leaflet.Map.prototype, 'setView');
		const fire = vi.spyOn(leaflet.Map.prototype, 'fire');
		const view = render(MapPointEditor, {
			mode: 'reveal',
			mapConfig,
			showCorrect: false,
			showGuesses: false,
			correctPoint: { lat: 48.86, lng: 2.33 },
			guessMarkers: [{ id: 'one', name: 'Player', point: { lat: 59.4, lng: 24.7 } }]
		});
		await vi.dynamicImportSettled();
		await tick();
		await vi.advanceTimersByTimeAsync(10);
		await view.rerender({
			showCorrect: true,
			showGuesses: true,
			scoringAnswer: {
				correct_point: { lat: 48.86, lng: 2.33 },
				scoring_mode: 'bands',
				max_points: 10,
				bands: [{ distance_m: 100000, points: 5 }]
			}
		});
		await vi.advanceTimersByTimeAsync(5000);
		expect(fly).toHaveBeenCalledTimes(1);
		const moves = move.mock.calls.length;
		const events = fire.mock.calls.length;
		await vi.advanceTimersByTimeAsync(5000);
		expect(move).toHaveBeenCalledTimes(moves);
		expect(fire).toHaveBeenCalledTimes(events);
		expect(view.container.querySelectorAll('.map-radius-label').length).toBeGreaterThan(0);
		await view.rerender({
			guessMarkers: [{ id: 'one', name: 'Player', point: { lat: 59.45, lng: 24.8 } }]
		});
		await vi.advanceTimersByTimeAsync(5000);
		expect(fly).toHaveBeenCalledTimes(2);
		expect(view.container.querySelectorAll('.map-guess-marker')).toHaveLength(1);
	});
});

it('settles in the full answer reveal screen after a submission update', async () => {
	const leaflet = await import('leaflet');
	const fly = vi.spyOn(leaflet.Map.prototype, 'flyTo');
	const addLayer = vi.spyOn(leaflet.Map.prototype, 'addLayer');
	const step: RuntimeStepState = {
		id: 'map',
		title: 'Map',
		input_kind: 'map',
		input_enabled: false,
		input_options: [],
		evaluation_type: 'map_distance',
		evaluation_points: 10,
		timer: { seconds: 30, enforced: false },
		map: DEFAULT_MAP_CONFIG
	};
	const view = render(StepDisplayPreview, {
		step,
		displayPhase: 'answer_reveal',
		layoutMode: 'host-stage',
		revealedAnswer: {
			value: {
				correct_point: { lat: 48.86, lng: 2.33 },
				scoring_mode: 'bands',
				max_points: 10,
				bands: [{ distance_m: 100000, points: 5 }]
			}
		},
		players: [{ id: 'one', name: 'Player', game_id: 'game', score: 0, status: 'connected' }],
		submissions: [{ player_id: 'one', value: { lat: 59.4, lng: 24.7 }, reviewed: false }]
	});
	await vi.dynamicImportSettled();
	await tick();
	await vi.advanceTimersByTimeAsync(100);
	await view.rerender({ submissionCount: 1 });
	await vi.advanceTimersByTimeAsync(5000);
	expect(fly).toHaveBeenCalledTimes(1);
	const layersAdded = addLayer.mock.calls.length;
	for (let i = 0; i < 10; i += 1) {
		await view.rerender({ step: structuredClone(step) });
		await vi.advanceTimersByTimeAsync(100);
	}
	expect(addLayer).toHaveBeenCalledTimes(layersAdded);
	await vi.advanceTimersByTimeAsync(5000);
	expect(fly).toHaveBeenCalledTimes(1);
	expect(view.container.querySelectorAll('.map-point-marker-correct')).toHaveLength(1);
});

it('cancels queued viewport work when the reveal is removed', async () => {
	const view = render(MapPointEditor, { mode: 'reveal' });
	await vi.dynamicImportSettled();
	await tick();
	await vi.advanceTimersByTimeAsync(5000);
	await view.rerender({ correctPoint: { lat: 59.4, lng: 24.7 } });
	expect(vi.getTimerCount()).toBeGreaterThan(0);
	view.unmount();
	expect(vi.getTimerCount()).toBe(0);
});

it('reuses the vector basemap across snapshots and removes it on switching or teardown', async () => {
	const mapConfig = { ...DEFAULT_MAP_CONFIG, base_layer: 'light_nolabels' as const };
	const view = render(MapPointEditor, { mode: 'player', mapConfig });
	await vi.dynamicImportSettled();
	await tick();
	expect(createOpenFreeMapLayer).toHaveBeenCalledTimes(1);
	const firstLayer = vi.mocked(createOpenFreeMapLayer).mock.results[0].value;
	expect(firstLayer.onAdd).toHaveBeenCalledTimes(1);
	await view.rerender({ mapConfig: structuredClone(mapConfig) });
	await vi.dynamicImportSettled();
	expect(createOpenFreeMapLayer).toHaveBeenCalledTimes(1);
	await view.rerender({ baseLayer: 'osm' });
	expect(firstLayer.onRemove).toHaveBeenCalledTimes(1);
	await view.rerender({ baseLayer: 'light_nolabels' });
	await vi.dynamicImportSettled();
	expect(createOpenFreeMapLayer).toHaveBeenCalledTimes(2);
	const secondLayer = vi.mocked(createOpenFreeMapLayer).mock.results[1].value;
	view.unmount();
	expect(secondLayer.onRemove).toHaveBeenCalledTimes(1);
});
