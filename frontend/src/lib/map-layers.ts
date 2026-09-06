export type MapBaseLayerId = NonNullable<MapInputConfig['base_layer']>;

export type MapTileLayerDefinition = {
	id: MapBaseLayerId;
} & ({ type: 'raster'; url: string; maxZoom: number; attribution: string } | { type: 'vector' });

export const MAP_TILE_LAYERS: Record<MapBaseLayerId, MapTileLayerDefinition> = {
	osm: {
		id: 'osm',
		type: 'raster',
		url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
		maxZoom: 19,
		attribution: '&copy; OpenStreetMap contributors'
	},
	light_nolabels: {
		id: 'light_nolabels',
		type: 'vector'
	}
};

export function getMapTileLayerDefinition(
	layer: MapInputConfig['base_layer'] = 'osm'
): MapTileLayerDefinition {
	return MAP_TILE_LAYERS[layer ?? 'osm'] ?? MAP_TILE_LAYERS.osm;
}
