import 'maplibre-gl/dist/maplibre-gl.css';
import { maplibreGL } from '@maplibre/maplibre-gl-leaflet';
import { createOpenFreeMapStyle, OPEN_FREE_MAP_ATTRIBUTION } from './openfreemap-style';

export function createOpenFreeMapLayer() {
	return maplibreGL({
		style: createOpenFreeMapStyle(),
		interactive: false,
		attributionControl: { customAttribution: OPEN_FREE_MAP_ATTRIBUTION }
	});
}
