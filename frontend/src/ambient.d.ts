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
type UserRole = 'admin' | 'user';
type DefinitionVisibility = 'private' | 'login_required' | 'public';

type User = {
	id: string;
	email: string;
	display_name: string;
	role: UserRole;
};

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
	starter_id?: string;
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
	avatar_kind?: 'preset' | 'custom';
	avatar_preset_key?: string;
	avatar_url?: string;
	avatar_asset_id?: string;
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
	visibility: DefinitionVisibility;
	owner_user_id?: string;
	owner_display_name?: string;
	can_edit: boolean;
};

type GameDefinition = {
	id: string;
	title: string;
	description?: string;
	visibility?: DefinitionVisibility;
	owner_user_id?: string;
	owner_display_name?: string;
	can_edit?: boolean;
	rounds: RoundDefinition[];
};

type RoundDefinition = {
	id: string;
	title?: string;
	steps: StepDefinition[];
};

type ImageMediaDefinition = {
	type_: 'image';
	src: string;
	reveal: string;
	loop: boolean;
	blur_circle_background?: 'blur' | 'solid';
	blur_circle_background_color?: string;
	zoom_start?: number;
	zoom_origin_x?: number;
	zoom_origin_y?: number;
};

type AudioMediaDefinition = {
	type_: 'audio';
	src: string;
	reveal: string;
	loop: boolean;
};

type VideoMediaDefinition = {
	type_: 'video';
	src: string;
	reveal: string;
	loop: boolean;
	autoplay?: boolean;
};

type StepMediaDefinition = ImageMediaDefinition | AudioMediaDefinition | VideoMediaDefinition;

type StepDefinition = {
	id: string;
	title: string;
	body?: string;
	media?: StepMediaDefinition;
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
	disabled_buzzer_player_ids: string[];
};

type AnswerJudgedEvent = {
	type_: 'answer_judged';
	player_id: string;
	accepted: boolean;
	source: 'host_review' | 'auto_evaluation';
	input_kind: PlayerInputKind;
	batch_id: string;
	batch_index: number;
	batch_size: number;
};

type RuntimeTimerState = {
	seconds?: number;
	enforced: boolean;
	started_at?: number;
	ends_at?: number;
	remaining_seconds?: number;
};

type RuntimeImageMediaState = {
	type_: 'image';
	src: string;
	paused: boolean;
	reveal?: string;
	loop: boolean;
	blur_circle_background?: 'blur' | 'solid';
	blur_circle_background_color?: string;
	zoom_start?: number;
	zoom_origin_x?: number;
	zoom_origin_y?: number;
	reveal_state: string;
	reveal_started_at?: number;
	reveal_elapsed_seconds: number;
	reveal_duration_seconds?: number;
};

type RuntimeAudioMediaState = {
	type_: 'audio';
	src: string;
	paused: boolean;
	reveal?: string;
	loop: boolean;
	reveal_state: string;
	reveal_started_at?: number;
	reveal_elapsed_seconds: number;
	reveal_duration_seconds?: number;
};

type RuntimeVideoMediaState = {
	type_: 'video';
	src: string;
	paused: boolean;
	reveal?: string;
	loop: boolean;
	autoplay?: boolean;
	playback_revision?: number;
	reveal_state: string;
	reveal_started_at?: number;
	reveal_elapsed_seconds: number;
	reveal_duration_seconds?: number;
};

type RuntimeMediaState = RuntimeImageMediaState | RuntimeAudioMediaState | RuntimeVideoMediaState;

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

type RuntimeRoundState = {
	id: string;
	title?: string;
	number: number;
	total: number;
};

type RuntimeStepItemState = {
	type_: 'step';
	step: RuntimeStepState;
};

type RuntimeRoundIntroItemState = {
	type_: 'round_intro';
	round: RuntimeRoundState;
	duration_seconds: number;
};

type RuntimeItemState = RuntimeStepItemState | RuntimeRoundIntroItemState;

type RuntimeLobbyState = {
	id: string;
	join_code: string;
	definition_id?: string;
	host_enabled: boolean;
	starter_id?: string;
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

type FinalStandingEntry = {
	player_id: string;
	name: string;
	score: number;
	place: number;
	avatar_kind?: 'preset' | 'custom';
	avatar_preset_key?: string;
	avatar_url?: string;
};

type EndGameStatCard = {
	id: string;
	label: string;
	winner_player_ids: string[];
	value: number;
	unit?: string;
	description?: string;
};

type EndGameState = {
	revealed: boolean;
	sequence_stage: string;
	autoplay_enabled: boolean;
	final_standings: FinalStandingEntry[];
	podium: FinalStandingEntry[];
	stats_cards: EndGameStatCard[];
};

type RuntimeSnapshotEvent = {
	type_: 'runtime_snapshot';
	revision: number;
	lobby: RuntimeLobbyState;
	players: Player[];
	active_item?: RuntimeItemState | null;
	active_round?: RuntimeRoundState | null;
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
	host_answer?: RevealedAnswer;
	submissions: SubmissionItem[];
	end_game?: EndGameState;
};

type RuntimePatchEvent = {
	type_: 'runtime_patch';
	base_revision: number;
	revision: number;
	changes: {
		lobby?: Partial<RuntimeLobbyState>;
		players?: Player[];
		active_item?: RuntimeItemState | null;
		active_round?: RuntimeRoundState | null;
		active_step?: RuntimeStepState;
		display_phase?: string;
		scoreboard_visible?: boolean;
		buzzer_active?: boolean;
		buzzed_player_id?: string;
		disabled_buzzer_player_ids?: string[];
		submitted_player_ids?: string[];
		submission_count?: number;
		pending_review_count?: number;
		revealed_submission?: RevealedSubmission;
		revealed_answer?: RevealedAnswer;
		host_answer?: RevealedAnswer;
		submissions?: SubmissionItem[];
		end_game?: EndGameState;
	};
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

type MediaPlaybackEvent = {
	type_: 'media_playback';
	paused?: boolean;
	restart?: boolean;
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

type ResyncRequestEvent = {
	type_: 'resync_request';
	last_revision?: number;
};

type RevealEndGameEvent = {
	type_: 'reveal_end_game';
};

type AdvanceEndGameStageEvent = {
	type_: 'advance_end_game_stage';
};

type ToggleEndGameAutoplayEvent = {
	type_: 'toggle_end_game_autoplay';
	enabled: boolean;
};

type PlayerReactionEvent = {
	type_: 'player_reaction';
	player_id: string;
	reaction: '😂' | '🔥' | '👏' | '😱' | '💩' | '🤮';
	instance_id: string;
	emitted_at: number;
};

type HostGameState = Lobby & {
	lastRevision: number;
	activeItem?: RuntimeItemState;
	activeStep?: RuntimeStepState;
	activeRound?: RuntimeRoundState;
	displayPhase: string;
	scoreboardVisible: boolean;
	buzzerActive: boolean;
	buzzedPlayerId?: string;
	disabledBuzzerPlayerIds: string[];
	submissionCount: number;
	pendingReviewCount: number;
	revealedSubmission?: RevealedSubmission;
	revealedAnswer?: RevealedAnswer;
	endGame?: EndGameState;
	lastReaction?: PlayerReactionEvent;
};

type ControllerState = {
	id: string;
	players: Player[];
	lastRevision: number;
	isHost: boolean;
	gameState: GameState;
	lobbyPhase: string;
	currentStep: number;
	hostEnabled: boolean;
	starterPlayerId?: string;
	activeItem?: RuntimeItemState;
	activeRound?: RuntimeRoundState;
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
	hostAnswer?: RevealedAnswer;
	submissions: SubmissionItem[];
	endGame?: EndGameState;
	lastReaction?: PlayerReactionEvent;
};

type YouTubePlayerState = -1 | 0 | 1 | 2 | 3 | 5;

type YouTubePlayer = {
	destroy: () => void;
	getPlayerState: () => YouTubePlayerState;
	pauseVideo: () => void;
	playVideo: () => void;
	seekTo: (seconds: number, allowSeekAhead: boolean) => void;
};

type YouTubeNamespace = {
	PlayerState: {
		BUFFERING: YouTubePlayerState;
		PLAYING: YouTubePlayerState;
	};
	Player: new (
		element: HTMLElement,
		config: {
			videoId: string;
			playerVars?: Record<string, string | number>;
			events?: {
				onReady?: () => void;
				onStateChange?: (event: { data: YouTubePlayerState }) => void;
			};
		}
	) => YouTubePlayer;
};

interface Window {
	YT?: YouTubeNamespace;
	onYouTubeIframeAPIReady?: () => void;
}
