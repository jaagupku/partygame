type ConnectionStatus = 'connected' | 'disconnected';
type GameState = 'waiting_for_players' | 'running' | 'paused';
type Controller = 'buzzer_game';
type Display = 'questionare';

type Lobby = {
	id: string;
	join_code: string;
	host_id?: string;
	players: Player[];
	connection: ConnectionStatus;
	state: GameState;
	definition_id?: string;
	current_step?: number;
	phase?: string;
	active_game?: string;
};

type Component = {
	type_: 'component_spec';
	display: Display;
	controller: Controller;
};

type Player = {
	id: string;
	name: string;
	game_id: string;
	score: number;
	status: ConnectionStatus;
	isHost?: boolean;
};

type ConnectedToLobby = {
	player: Player;
	lobby: Lobby;
};

type PlayerJoinedEvent = {
	type_: 'player_joined';
	player: Player;
};

type PlayerConnectedEvent = {
	type_: 'player_connected';
	player_id: string;
};

type PlayerDisconnectedEvent = {
	type_: 'player_disconnected';
	player_id: string;
};

type SetHostEvent = {
	type_: 'set_host';
	player_id: string;
};

type KickPlayerEvent = {
	type_: 'kick_player';
	player_id: string;
};

type StartGameEvent = {
	type_: 'start_game';
};

type BuzzerStateEvent = {
	type_: 'buzzer_state';
	state: 'active' | 'deactive';
	disable_activator: boolean;
};

type BuzzerClickedEvent = {
	type_: 'buzzer_clicked';
	player_id: string;
};

type ComponentRuntimeState = {
	type_: 'display_text_image' | 'player_input' | 'buzzer' | string;
	props?: Record<string, unknown>;
	answers?: Record<string, unknown>;
	step_id?: string;
	state?: string;
	buzzed_player?: string;
};

type ComponentStateUpdatedEvent = {
	type_: 'component_state_updated';
	component_id: string;
	state: ComponentRuntimeState;
};

type StepAdvancedEvent = {
	type_: 'step_advanced';
	step_index: number;
};

type ScoresUpdatedEvent = {
	type_: 'scores_updated';
	updates: Record<string, number>;
};

type ControllerState = {
	id: string;
	isHost: boolean;
	gameState: GameState;
	currentStep: number;
	questionText: string;
	questionImage?: string;
	activeInputComponentId?: string;
	inputKind: 'text' | 'number' | 'ordering';
};

type UpdateScoreEvent = {
	type_: 'update_score';
	player_id: string;
	add_score: number;
	set_score?: number;
};
