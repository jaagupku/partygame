import type { StyleSpecification } from 'maplibre-gl';

export const OPEN_FREE_MAP_ATTRIBUTION =
	'<a href="https://openfreemap.org/">OpenFreeMap</a> &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> Data from <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

// A deliberately label-free style: no symbol layers, glyphs or sprites can reveal answers.
// The OpenMapTiles schema is served by OpenFreeMap's public, keyless endpoint.
export function createOpenFreeMapStyle(): StyleSpecification {
	return {
		version: 8,
		sources: {
			openmaptiles: { type: 'vector', url: 'https://tiles.openfreemap.org/planet' }
		},
		layers: [
			{ id: 'background', type: 'background', paint: { 'background-color': '#fafaf8' } },
			{
				id: 'landcover',
				type: 'fill',
				source: 'openmaptiles',
				'source-layer': 'landcover',
				paint: { 'fill-color': '#e8ece7', 'fill-opacity': 0.5 }
			},
			{
				id: 'parks',
				type: 'fill',
				source: 'openmaptiles',
				'source-layer': 'park',
				paint: { 'fill-color': '#e6ece4', 'fill-opacity': 0.6 }
			},
			{
				id: 'water',
				type: 'fill',
				source: 'openmaptiles',
				'source-layer': 'water',
				paint: { 'fill-color': '#d4dadd' }
			},
			{
				id: 'waterways',
				type: 'line',
				source: 'openmaptiles',
				'source-layer': 'waterway',
				paint: {
					'line-color': '#d4dadd',
					'line-width': ['interpolate', ['linear'], ['zoom'], 6, 0.5, 16, 2]
				}
			},
			{
				id: 'buildings',
				type: 'fill',
				source: 'openmaptiles',
				'source-layer': 'building',
				minzoom: 13,
				paint: { 'fill-color': '#e1e3e1', 'fill-outline-color': '#d6d8d6' }
			},
			{
				id: 'roads',
				type: 'line',
				source: 'openmaptiles',
				'source-layer': 'transportation',
				filter: [
					'in',
					'class',
					'motorway',
					'trunk',
					'primary',
					'secondary',
					'tertiary',
					'minor',
					'service',
					'path'
				],
				paint: {
					'line-color': '#ffffff',
					'line-width': ['interpolate', ['linear'], ['zoom'], 5, 0.5, 12, 1.5, 18, 6]
				}
			},
			{
				id: 'regional-boundaries',
				type: 'line',
				source: 'openmaptiles',
				'source-layer': 'boundary',
				filter: ['all', ['>', 'admin_level', 2], ['<=', 'admin_level', 6]],
				paint: { 'line-color': '#e0d6d6', 'line-width': 0.6, 'line-dasharray': [3, 2] }
			},
			{
				id: 'country-boundaries',
				type: 'line',
				source: 'openmaptiles',
				'source-layer': 'boundary',
				filter: ['==', 'admin_level', 2],
				paint: { 'line-color': '#cbbfc2', 'line-width': 1 }
			}
		]
	};
}
