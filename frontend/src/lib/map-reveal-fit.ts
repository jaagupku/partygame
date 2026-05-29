export type MapRevealFitTarget =
	| {
			kind: 'point';
			point: MapPoint;
			zoom: number;
	  }
	| {
			kind: 'bounds';
			points: MapPoint[];
			padding: [number, number];
			maxZoom: number;
	  };

type MapRevealFitMarker = {
	point: MapPoint;
};

export function revealFitKey(points: MapPoint[]): string {
	return points
		.map((point) => `${point.lat.toFixed(6)},${point.lng.toFixed(6)}`)
		.sort()
		.join('|');
}

export function buildMapRevealFitTarget(
	guessMarkers: MapRevealFitMarker[],
	correctPoint: MapPoint | null,
	options: {
		includeCorrect?: boolean;
		maxZoom?: number;
		padding?: [number, number];
		extraPoints?: MapPoint[];
	} = {}
): MapRevealFitTarget | null {
	const points = [
		...guessMarkers.map((marker) => marker.point),
		...(correctPoint && options.includeCorrect !== false ? [correctPoint] : []),
		...(options.extraPoints ?? [])
	];
	if (points.length === 0) {
		return null;
	}
	if (points.length === 1) {
		return {
			kind: 'point',
			point: points[0],
			zoom: Math.min(options.maxZoom ?? 16, 16)
		};
	}
	return {
		kind: 'bounds',
		points,
		padding: options.padding ?? [72, 72],
		maxZoom: options.maxZoom ?? 17
	};
}
