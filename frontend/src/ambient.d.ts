type ConnectionStatus = 'connected' | 'disconnected';
type GameState = 'waiting_for_players' | 'running' | 'paused';
type PlayerInputKind = 'none' | 'buzzer' | 'text' | 'number' | 'ordering' | 'radio' | 'checkbox';
type EvaluationType =
	| 'none'
	| 'host_judged'
	| 'exact_text'
	| 'exact_number'
	| 'closest_number'
	| 'ordering_match'
	| 'multi_select_weighted';

type CheckboxOptionScore = {
	option: string;
	points: number;
};

type CheckboxWeightedAnswer = {
	option_scores: CheckboxOptionScore[];
};

type Lobby = {
	id: string;
	join_code: string;
	host_id?: string;
	host_enabled: boolean;
	players: Player[];
	connection: ConnectionStatus;
	state: GameState;
	definition_id?: string;
	current_step?: number;
	phase?: string;
	active_game?: string;
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

type DefinitionSummary = {
	id: string;
	title: string;
	description?: string;
};

type GameDefinition = {
	id: string;
	title: string;
	description?: string;
	rounds: RoundDefinition[];
};

type RoundDefinition = {
	id: string;
	title?: string;
	steps: StepDefinition[];
};

type StepDefinition = {
	id: string;
	title: string;
	body?: string;
	media?: {
		type_: string;
		src: string;
		reveal: string;
		loop: boolean;
	};
	timer: {
		seconds?: number;
		enforced: boolean;
	};
	player_input: {
		kind: PlayerInputKind;
		prompt?: string;
		placeholder?: string;
		options: string[];
		min_value?: number;
		max_value?: number;
		step?: number;
	};
	evaluation: {
		type_: EvaluationType;
		points: number;
		answer?: string | number | string[] | CheckboxWeightedAnswer | null;
	};
	host_behavior: {
		reveal_answers: boolean;
		show_submissions: boolean;
		allow_custom_points: boolean;
	};
};

type MediaAsset = {
	id: string;
	kind: 'image' | 'audio' | 'video';
	storage_path: string;
	original_filename: string;
	content_type: string;
	size_bytes: number;
	public_url: string;
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

type ResetStepEvent = {
	type_: 'reset_step';
};

type ShowAnswerRevealEvent = {
	type_: 'show_answer_reveal';
};

type ShowQuestionEvent = {
	type_: 'show_question';
};

type ScoreboardVisibilityEvent = {
	type_: 'scoreboard_visibility';
	visible: boolean;
};

type BuzzerStateEvent = {
	type_: 'buzzer_state';
	active: boolean;
};

type BuzzerClickedEvent = {
	type_: 'buzzer_clicked';
	player_id: string;
};

type BuzzerReviewedEvent = {
	type_: 'buzzer_reviewed';
	player_id: string;
	accepted: boolean;
};

type RuntimeTimerState = {
	seconds?: number;
	enforced: boolean;
	started_at?: number;
	ends_at?: number;
	remaining_seconds?: number;
};

type RuntimeMediaState = {
	type_: string;
	src: string;
	reveal?: string;
	loop: boolean;
	reveal_state: string;
	reveal_started_at?: number;
	reveal_elapsed_seconds: number;
	reveal_duration_seconds?: number;
};

type RuntimeStepState = {
	id: string;
	title: string;
	body?: string;
	evaluation_type: string;
	evaluation_points: number;
	input_enabled: boolean;
	input_kind: PlayerInputKind;
	input_prompt?: string;
	input_placeholder?: string;
	input_options: string[];
	slider_min?: number;
	slider_max?: number;
	slider_step?: number;
	media?: RuntimeMediaState;
	timer: RuntimeTimerState;
};

type RuntimeLobbyState = {
	id: string;
	join_code: string;
	definition_id?: string;
	host_enabled: boolean;
	host_id?: string;
	state: GameState;
	phase: string;
	current_step: number;
};

type RevealedSubmission = {
	player_id: string;
	value: unknown;
};

type RevealedAnswer = {
	value: unknown;
};

type RuntimeSnapshotEvent = {
	type_: 'runtime_snapshot';
	lobby: RuntimeLobbyState;
	active_step?: RuntimeStepState;
	display_phase: string;
	scoreboard_visible: boolean;
	buzzer_active: boolean;
	buzzed_player_id?: string;
	disabled_buzzer_player_ids: string[];
	submitted_player_ids: string[];
	submission_count: number;
	pending_review_count: number;
	revealed_submission?: RevealedSubmission;
	revealed_answer?: RevealedAnswer;
};

type SubmissionItem = {
	player_id: string;
	value: unknown;
	reviewed: boolean;
};

type SubmissionsUpdatedEvent = {
	type_: 'submissions_updated';
	items: SubmissionItem[];
};

type RevealedSubmissionEvent = {
	type_: 'revealed_submission';
	submission?: RevealedSubmission;
};

type StepAdvancedEvent = {
	type_: 'step_advanced';
	step_index: number;
};

type ScoresUpdatedEvent = {
	type_: 'scores_updated';
	updates: Record<string, number>;
};

type CloseStepEvent = {
	type_: 'close_step';
};

type ReviewSubmissionEvent = {
	type_: 'review_submission';
	player_id: string;
	accepted: boolean;
	points_override?: number;
};

type UpdateScoreEvent = {
	type_: 'update_score';
	player_id: string;
	add_score: number;
	set_score?: number;
};

type HostGameState = Lobby & {
	activeStep?: RuntimeStepState;
	displayPhase: string;
	scoreboardVisible: boolean;
	buzzerActive: boolean;
	buzzedPlayerId?: string;
	disabledBuzzerPlayerIds: string[];
	submissionCount: number;
	pendingReviewCount: number;
	revealedSubmission?: RevealedSubmission;
	revealedAnswer?: RevealedAnswer;
};

type ControllerState = {
	id: string;
	isHost: boolean;
	gameState: GameState;
	lobbyPhase: string;
	currentStep: number;
	hostEnabled: boolean;
	activeStep?: RuntimeStepState;
	displayPhase: string;
	scoreboardVisible: boolean;
	buzzerActive: boolean;
	buzzedPlayerId?: string;
	disabledBuzzerPlayerIds: string[];
	submittedPlayerIds: string[];
	hasSubmitted: boolean;
	submissionCount: number;
	pendingReviewCount: number;
	revealedSubmission?: RevealedSubmission;
	revealedAnswer?: RevealedAnswer;
	submissions: SubmissionItem[];
};
