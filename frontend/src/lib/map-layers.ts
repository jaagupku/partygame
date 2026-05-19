export type MapBaseLayerId = NonNullable<MapInputConfig['base_layer']>;

export type MapTileLayerDefinition = {
	id: MapBaseLayerId;
	label: string;
	url: string;
	maxZoom: number;
	attribution: string;
};

export const MAP_TILE_LAYERS: Record<MapBaseLayerId, MapTileLayerDefinition> = {
	osm: {
		id: 'osm',
		label: 'OSM with labels',
		url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
		maxZoom: 19,
		attribution: '&copy; OpenStreetMap contributors'
	},
	light_nolabels: {
		id: 'light_nolabels',
		label: 'Simplified without labels',
		url: 'https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png',
		maxZoom: 20,
		attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
	}
};

export function getMapTileLayerDefinition(
	layer: MapInputConfig['base_layer'] = 'osm'
): MapTileLayerDefinition {
	return MAP_TILE_LAYERS[layer ?? 'osm'] ?? MAP_TILE_LAYERS.osm;
}
