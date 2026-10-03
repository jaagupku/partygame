export type GameType = {
	id: string;
	localization_key: 'drawingMashup' | 'trivia' | 'priceGuessing' | 'calorieGuessing';
	availability: 'available' | 'coming_soon';
	host_modes: ('hosted' | 'automatic')[];
};

export async function loadGameCatalog(): Promise<GameType[]> {
	const response = await fetch('/api/v1/game-types');
	if (!response.ok) throw new Error('Could not load game catalog');
	return response.json();
}
