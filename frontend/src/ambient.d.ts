type ConnectionStatus = 'connected' | 'disconnected';
type GameState = 'waiting_for_players' | 'running' | 'paused';
type PlayerInputKind =
	| 'none'
	| 'buzzer'
	| 'text'
	| 'number'
	| 'ordering'
	| 'radio'
	| 'checkbox'
	| 'map'
	| 'drawing';
type EvaluationType =
	| 'none'
	| 'host_judged'
	| 'exact_text'
	| 'exact_number'
	| 'closest_number'
	| 'ordering_match'
	| 'multi_select_weighted'
	| 'map_distance'
	| 'favorite_vote';
type UserRole = 'admin' | 'user';
type DefinitionVisibility = 'private' | 'login_required' | 'public';
type RevealCurve = [number, number, number, number];
type DefinitionThemeMode = 'light' | 'dark' | 'system';
type DefinitionThemePalette = 'party' | 'midnight' | 'candy' | 'forest';

type DefinitionTheme = {
	mode?: DefinitionThemeMode;
	palette?: DefinitionThemePalette;
	background?: string | null;
	surface?: string | null;
	ink?: string | null;
	primary?: string | null;
	accent?: string | null;
};

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

type NumberToleranceBand = {
	distance: number;
	points: number;
	label?: string;
};

type MapPoint = {
	lat: number;
	lng: number;
};

type MapBounds = {
	north: number;
	south: number;
	east: number;
	west: number;
};

type MapInputConfig = {
	selection_mode: 'point';
	base_layer?: 'osm' | 'light_nolabels';
	bounds: MapBounds;
	initial_center: MapPoint;
	initial_zoom: number;
	min_zoom?: number;
	max_zoom?: number;
};

type MapDistanceBand = {
	distance_m: number;
	points: number;
	label?: string;
};

type MapDistanceAnswer = {
	correct_point: MapPoint;
	scoring_mode: 'bands' | 'linear';
	max_points: number;
	zero_distance_m?: number | null;
	full_credit_distance_m?: number | null;
	bands?: MapDistanceBand[];
};

type DrawingPoint = {
	x: number;
	y: number;
};

type DrawingStroke = {
	color: string;
	size: number;
	eraser: boolean;
	points: DrawingPoint[];
};

type CompactDrawingStroke = [number, number, 0 | 1, number[]];

type DrawingSubmission = {
	w: 512;
	h: 384;
	s: CompactDrawingStroke[];
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
	theme?: DefinitionTheme | null;
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
	blur_amount?: number;
	blur_circle_start_size?: number;
	blur_circle_background?: 'blur' | 'solid';
	blur_circle_background_color?: string;
	blur_reveal_curve?: RevealCurve;
	blur_circle_reveal_curve?: RevealCurve;
	zoom_reveal_curve?: RevealCurve;
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
	hide_youtube_title?: boolean;
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
		map?: MapInputConfig;
	};
	evaluation: {
		type_: EvaluationType;
		points: number;
		answer?: string | number | string[] | CheckboxWeightedAnswer | MapDistanceAnswer | null;
		max_distance?: number;
		number_bands?: NumberToleranceBand[];
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

type ShowPreviousRevealEvent = {
	type_: 'show_previous_reveal';
};

type ShowNextRevealEvent = {
	type_: 'show_next_reveal';
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

type CollectPlayerDraftsEvent = {
	type_: 'collect_player_drafts';
	step_id: string;
	reason: 'timer_expired' | 'host_reveal';
};

type SubmissionRejectedReason =
	| 'invalid_drawing'
	| 'invalid_submission'
	| 'duplicate_submission'
	| 'step_closed';

type SubmissionRejectedEvent = {
	type_: 'submission_rejected';
	player_id: string;
	reason: SubmissionRejectedReason;
	details?: string | null;
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
	volume?: number;
	reveal?: string;
	loop: boolean;
	blur_amount?: number;
	blur_circle_start_size?: number;
	blur_circle_background?: 'blur' | 'solid';
	blur_circle_background_color?: string;
	blur_reveal_curve?: RevealCurve;
	blur_circle_reveal_curve?: RevealCurve;
	zoom_reveal_curve?: RevealCurve;
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
	volume?: number;
	reveal?: string;
	loop: boolean;
	playback_revision?: number;
	reveal_state: string;
	reveal_started_at?: number;
	reveal_elapsed_seconds: number;
	reveal_duration_seconds?: number;
};

type RuntimeVideoMediaState = {
	type_: 'video';
	src: string;
	paused: boolean;
	volume?: number;
	reveal?: string;
	loop: boolean;
	autoplay?: boolean;
	hide_youtube_title?: boolean;
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
	evaluation_answer?: unknown;
	max_points?: number;
	input_enabled: boolean;
	input_kind: PlayerInputKind;
	input_prompt?: string;
	input_placeholder?: string;
	input_options: string[];
	slider_min?: number;
	slider_max?: number;
	slider_step?: number;
	map?: MapInputConfig;
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

type NextHostAction = {
	kind:
		| 'answer_reveal'
		| 'next_question'
		| 'round_intro'
		| 'finale'
		| 'blocked_review'
		| 'reactivate_buzzers';
	title?: string;
	disabled: boolean;
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
	answer_counts?: Record<string, number>;
	correct_counts?: Record<string, number>;
	id: string;
	label: string;
	winner_player_ids: string[];
	value: number;
	unit?: string;
	description?: string;
	emoji?: string;
	headline?: string;
	reaction_key?: import('$lib/reactions').ReactionId;
};

type EndGameState = {
	revealed: boolean;
	sequence_stage: string;
	autoplay_enabled: boolean;
	final_standings: FinalStandingEntry[];
	podium: FinalStandingEntry[];
	stats_cards: EndGameStatCard[];
	highlight_card_ids?: string[];
};

type GameStatSummary = {
	game_id: string;
	join_code: string;
	definition_id?: string | null;
	definition_title?: string | null;
	host_enabled: boolean;
	started_at?: string | null;
	finished_at: string;
	player_count: number;
	round_count: number;
	step_count: number;
	summary: {
		scoreboard?: Array<{ player_id: string; name: string; score: number; place: number }>;
		answers?: {
			submitted_count?: number;
			reviewed_count?: number;
			answered_count?: number;
			correct_count?: number;
			wrong_count?: number;
			average_accuracy_percent?: number | null;
		};
		buzzers?: {
			buzz_count?: number;
			fastest_reaction_seconds?: number | null;
			median_reaction_seconds?: number | null;
			close_call_count?: number;
			close_call_threshold_seconds?: number;
		};
		reactions?: {
			total_reactions?: number;
			most_used_reaction?: string | null;
			reaction_counts?: Record<string, number>;
		};
	};
};

type GameStatSummaryList = {
	items: GameStatSummary[];
	total: number;
	limit: number;
	offset: number;
};

type RuntimeSnapshotEvent = {
	type_: 'runtime_snapshot';
	revision: number;
	lobby: RuntimeLobbyState;
	theme?: DefinitionTheme | null;
	players: Player[];
	active_item?: RuntimeItemState | null;
	next_item?: RuntimeItemState | null;
	next_host_action?: NextHostAction | null;
	active_round?: RuntimeRoundState | null;
	active_step?: RuntimeStepState;
	review_step_index?: number | null;
	reviewing_history: boolean;
	can_review_previous: boolean;
	can_review_next: boolean;
	display_phase: string;
	scoreboard_visible: boolean;
	buzzer_active: boolean;
	buzzed_player_id?: string;
	disabled_buzzer_player_ids: string[];
	submitted_player_ids: string[];
	submission_count: number;
	pending_review_count: number;
	drawing_items: DrawingVoteItem[];
	own_drawing_id?: string | null;
	drawing_voted_player_ids: string[];
	drawing_vote_count: number;
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
		theme?: DefinitionTheme | null;
		players?: Player[];
		active_item?: RuntimeItemState | null;
		next_item?: RuntimeItemState | null;
		next_host_action?: NextHostAction | null;
		active_round?: RuntimeRoundState | null;
		active_step?: RuntimeStepState;
		review_step_index?: number | null;
		reviewing_history?: boolean;
		can_review_previous?: boolean;
		can_review_next?: boolean;
		display_phase?: string;
		scoreboard_visible?: boolean;
		buzzer_active?: boolean;
		buzzed_player_id?: string;
		disabled_buzzer_player_ids?: string[];
		submitted_player_ids?: string[];
		submission_count?: number;
		pending_review_count?: number;
		drawing_items?: DrawingVoteItem[];
		own_drawing_id?: string | null;
		drawing_voted_player_ids?: string[];
		drawing_vote_count?: number;
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

type DrawingVoteItem = {
	id: string;
	label: string;
	value: unknown;
	player_id?: string | null;
	player_name?: string | null;
	vote_count: number;
	points_awarded: number;
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
	volume?: number;
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
	theme?: DefinitionTheme | null;
	activeItem?: RuntimeItemState;
	nextItem?: RuntimeItemState;
	nextHostAction?: NextHostAction;
	activeStep?: RuntimeStepState;
	activeRound?: RuntimeRoundState;
	displayPhase: string;
	reviewStepIndex?: number | null;
	reviewingHistory: boolean;
	canReviewPrevious: boolean;
	canReviewNext: boolean;
	scoreboardVisible: boolean;
	buzzerActive: boolean;
	buzzedPlayerId?: string;
	disabledBuzzerPlayerIds: string[];
	submissionCount: number;
	pendingReviewCount: number;
	drawingItems?: DrawingVoteItem[];
	ownDrawingId?: string;
	drawingVotedPlayerIds?: string[];
	drawingVoteCount?: number;
	revealedSubmission?: RevealedSubmission;
	revealedAnswer?: RevealedAnswer;
	submissions?: SubmissionItem[];
	endGame?: EndGameState;
	lastReaction?: PlayerReactionEvent;
};

type ControllerState = {
	id: string;
	players: Player[];
	lastRevision: number;
	theme?: DefinitionTheme | null;
	isHost: boolean;
	answerResult: 'correct' | 'wrong' | 'none';
	submissionError?: SubmissionRejectedReason;
	gameState: GameState;
	lobbyPhase: string;
	currentStep: number;
	hostEnabled: boolean;
	starterPlayerId?: string;
	activeItem?: RuntimeItemState;
	nextItem?: RuntimeItemState;
	nextHostAction?: NextHostAction;
	activeRound?: RuntimeRoundState;
	activeStep?: RuntimeStepState;
	displayPhase: string;
	reviewStepIndex?: number | null;
	reviewingHistory: boolean;
	canReviewPrevious: boolean;
	canReviewNext: boolean;
	scoreboardVisible: boolean;
	buzzerActive: boolean;
	buzzedPlayerId?: string;
	disabledBuzzerPlayerIds: string[];
	submittedPlayerIds: string[];
	hasSubmitted: boolean;
	submissionCount: number;
	pendingReviewCount: number;
	drawingItems: DrawingVoteItem[];
	ownDrawingId?: string;
	drawingVotedPlayerIds: string[];
	drawingVoteCount: number;
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
	setVolume: (volume: number) => void;
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
