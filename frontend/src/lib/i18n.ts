import { get, derived } from 'svelte/store';

import { createLocalStorageStore } from '$lib/local-storage-store';

export const locales = [
	{ code: 'en', label: 'English' },
	{ code: 'et', label: 'Eesti' }
] as const;

export type Locale = (typeof locales)[number]['code'];

const fallbackLocale: Locale = 'en';

type Widen<T> = T extends string
	? string
	: T extends number
		? number
		: T extends boolean
			? boolean
			: T extends (...args: infer Args) => infer Return
				? (...args: Args) => Return
				: T extends readonly (infer Item)[]
					? Widen<Item>[]
					: T extends object
						? { -readonly [Key in keyof T]: Widen<T[Key]> }
						: T;

function defineMessages<T>(value: T): Widen<T> {
	return value as Widen<T>;
}

const en = defineMessages({
	common: {
		appName: 'Party Game',
		language: 'Language',
		home: 'Home',
		back: 'Back',
		cancel: 'Cancel',
		close: 'Close',
		save: 'Save',
		saveDetails: 'Save Details',
		saveRound: 'Save Round',
		loading: 'Loading...',
		live: 'Live',
		disconnected: 'Disconnected',
		on: 'On',
		off: 'Off',
		host: 'Host',
		manageDefinitions: 'Manage definitions',
		createGame: 'Create Game',
		createDefinition: 'Create Definition',
		edit: 'Edit',
		remove: 'Remove',
		add: 'Add',
		preview: 'Preview',
		rounds: 'Rounds',
		steps: 'steps',
		selected: 'Selected',
		connection: 'Connection',
		question: 'Question',
		answerReveal: 'Answer Reveal',
		nowPlaying: 'Now Playing',
		revealedAnswer: 'Revealed answer',
		correctAnswer: 'Correct answer',
		waitingForNextQuestion: 'Waiting for next question...',
		finalResult: 'Final Result',
		score: 'Score',
		pointsWord: 'points',
		breadcrumb: 'Breadcrumb'
	},
	home: {
		title: 'Party Quiz Arena',
		subtitle: 'Pick how you want to enter the game.',
		create: 'Create',
		join: 'Join'
	},
	create: {
		title: 'Create Game',
		subtitle: 'Pick a definition, review it, and choose whether a host phone runs the show.',
		gameDefinition: 'Game definition',
		hostEnabledMode: 'Host-enabled mode',
		hostEnabledHelp: 'When on, the first joined player becomes the host controller.',
		definitionPreview: 'Definition Preview',
		loadingDefinitionDetails: 'Loading definition details...',
		noDefinitionSelected: 'No definition selected.',
		noDescriptionProvided: 'No description provided.'
	},
	join: {
		title: 'Join Game',
		subtitle: 'Set your player profile, then enter the 5-letter lobby code.',
		avatar: 'Avatar',
		playerFallback: 'Player',
		customPhotoAvatar: 'Custom photo avatar',
		preset: 'Preset',
		random: 'Random',
		hideAvatarOptions: 'Hide avatar options',
		changeAvatar: 'Tap to change avatar',
		name: 'Name',
		namePlaceholder: 'Your name',
		choosePresetAvatar: 'Choose a preset avatar',
		takePhotoOrChoose: 'Take a photo or choose one',
		photoHelp: 'Your image will be cropped into a square 256x256 avatar before upload.',
		useCameraPhoto: 'Use Camera / Photo',
		adjustPhoto: 'Drag to position the image and use zoom to frame your avatar.',
		uploading: 'Uploading...',
		useThisPhoto: 'Use this photo',
		customAvatarReady: 'Custom avatar ready for your next join.',
		joinCode: 'Join Code',
		joinCodePlaceholder: 'ABCDE',
		checkingSavedAvatar: 'Checking saved custom avatar...',
		couldNotJoinGame: 'Could not join game.',
		couldNotPrepareAvatar: 'Could not prepare avatar image.',
		couldNotUploadAvatar: 'Could not upload avatar.',
		joinAction: 'Join'
	},
	definitions: {
		title: 'Manage Definitions',
		subtitle:
			'Browse your saved game definitions and jump into the editor when you want to create or update one.',
		currentDefinitions: 'Current Definitions',
		noDefinitionsYet: 'No Definitions Yet',
		noDefinitionsHelp: 'Create your first definition to start building rounds and slides.',
		noDescriptionProvidedYet: 'No description provided yet.',
		definitionBadge: 'Definition',
		newDefinitionTitle: 'New Definition',
		editDefinitionTitle: 'Edit Definition',
		couldNotLoadDefinitions: 'Could not load definitions.',
		couldNotLoadDefinition: (definitionId: string) =>
			`Could not load definition "${definitionId}".`,
		definitionSaved: 'Definition saved.',
		couldNotSaveDefinition: 'Could not save definition.',
		untitledDefinition: 'Untitled Definition',
		newDefinitionBreadcrumb: 'New Definition',
		editDefinitionBreadcrumb: 'Edit Definition'
	},
	hostView: {
		hostLobbyTitle: 'Host Lobby',
		joinCode: 'Join code',
		hostMode: 'Host mode',
		useHostController: 'Use the host controller to start and run the game.',
		finalResultsReady:
			'Final results are ready. Reveal the finale from the host controller when you are set.',
		playerStatusWaiting: 'Waiting for players'
	},
	gameplay: {
		hostControllerTitle: 'Host Controller',
		playerControllerTitle: 'Player Controller',
		waitingForGameStart: 'Waiting for game to start.',
		youAreHostController: 'You are the host controller.',
		youCanStartAsFirstPlayer: 'You joined first, so you can start this hostless game.',
		youCanContinueInfoSlide: 'You joined first, so you can continue this information slide.',
		startGame: 'Start Game',
		finaleControls: 'Finale Controls',
		stage: 'Stage',
		autoplay: 'Autoplay',
		resetToPodium: 'Reset To Podium',
		nextFinaleStage: 'Next Finale Stage',
		disableAutoplay: 'Disable Autoplay',
		enableAutoplay: 'Enable Autoplay',
		buzzer: 'Buzzer',
		answerReceivedWaiting: 'Answer received. Waiting for the next step.',
		stepClosed: 'This step is closed.',
		buzzerChanceUsed: 'You already used your buzzer chance for this question.',
		buzzNow: 'Buzz now!',
		waitForHost: 'Wait for the host to continue.',
		yourAnswer: 'Your Answer',
		answerSubmitted: 'Your answer is in. You can submit again on the next step.',
		stepClosedAnswersDisabled: 'This step has been closed. New answers are disabled.',
		typeYourAnswer: 'Type your answer',
		enterNumber: 'Enter a number',
		submitAnswer: 'Submit Answer',
		orderingAnswer: 'Ordering Answer',
		orderSubmitted: 'Your order is submitted. You can reorder again on the next step.',
		reorderingDisabled: 'This step has been closed. Reordering is disabled.',
		dragItemsToOrder: 'Drag items into the order you want, then submit.',
		submitOrder: 'Submit Order',
		chooseOne: 'Choose One',
		choiceLocked: 'Your choice is locked in. You can choose again on the next step.',
		newSelectionsDisabled: 'This step has been closed. New selections are disabled.',
		tapOneOption: 'Tap one option to submit it immediately.',
		chooseOneOrMore: 'Choose One or More',
		selectionSubmitted: 'Your selection is submitted. You can choose again on the next step.',
		tapOptionsThenSubmit: 'Tap options to highlight them, then submit when you are ready.',
		submitSelection: 'Submit Selection',
		noPhoneInput: 'No phone input is required for this step.',
		gameComplete: 'Game complete.',
		scoreboardShowingOnMainScreen: 'Scoreboard is currently showing on the main screen.',
		revealFinaleFromHost: 'Use the host controller below to reveal the finale screen.',
		waitingForFinalResults: 'Waiting for the host to reveal the final results.',
		revealFinale: 'Reveal Finale',
		gameFinishedRevealEndScreen:
			'The game is finished. Reveal the end game screen when you are ready.',
		hostControls: 'Host Controls',
		phaseLabel: 'Phase',
		submissionsLabel: 'Submissions',
		pendingReviewLabel: 'Pending review',
		answered: 'answered',
		previous: 'Previous',
		advanceStep: 'Advance Step',
		next: 'Next',
		showAnswer: 'Show Answer',
		resetQuestion: 'Reset Question',
		hideScoreboard: 'Hide Scoreboard',
		showScoreboard: 'Show Scoreboard',
		videoPlayback: 'Video Playback',
		pauseMedia: 'Pause Video',
		resumeMedia: 'Resume Video',
		autoEvaluate: 'Auto Evaluate',
		disableBuzzer: 'Disable Buzzer',
		enableEligibleBuzzers: 'Enable Eligible Buzzers',
		reviewQueue: 'Review Queue',
		buzzedInFirst: 'Buzzed in first',
		acceptWithPoints: (points: number) => `Accept +${points}`,
		reject: 'Reject',
		waitingToReactivateBuzzers: 'Waiting for the host to reactivate eligible buzzers.',
		lockedOut: 'Locked out',
		noAnswersSubmittedYet: 'No answers submitted yet.',
		reveal: 'Reveal',
		reviewed: 'Reviewed',
		acceptCustomPoints: (points: number) => `Accept ${points > 0 ? '+' : ''}${points}`,
		manualScore: 'Manual Score',
		reactionBarTitle: 'Reaction Spam',
		reactionBarHelp: 'Tap fast to send fun reactions to the main screen.',
		reactionBurstOverlayLabel: 'Live audience reactions',
		reactionLabels: {
			laugh: 'Laugh reaction',
			fire: 'Fire reaction',
			clap: 'Clap reaction',
			shock: 'Shock reaction',
			poop: 'Poop reaction',
			vomit: 'Vomit reaction'
		}
	},
	timer: {
		timeRemaining: 'Time remaining',
		timerEnforced: 'Timer is enforced',
		timerAdvisory: 'Timer is advisory'
	},
	finale: {
		title: 'Final Results',
		thirdPlaceReveal: 'Third place reveal',
		secondPlaceReveal: 'Second place reveal',
		firstPlaceReveal: 'Champion reveal',
		bestMoments: 'Best moments from the match',
		fullScoreboard: 'Full final scoreboard',
		noFinalStandingsYet: 'No final standings yet.',
		place: (place: number) => `Place #${place}`,
		stageLabel: (stage: string): string =>
			stage === 'third_place'
				? 'Third Place'
				: stage === 'second_place'
					? 'Second Place'
					: stage === 'first_place'
						? 'First Place'
						: stage === 'stats'
							? 'Stats'
							: 'Scoreboard',
		noStatsYet: 'No Stats Yet',
		noStatsHelp: 'This game did not produce enough data for finale highlights.',
		finished: 'Finished',
		gameComplete: 'Game Complete',
		youWonTheGame: 'You won the game',
		topThreeFinish: 'Top 3 finish',
		finalStandingsIn: 'Final standings are in',
		notIncludedInStandings:
			'Your controller is connected, but you were not included in the final standings.'
	},
	editor: {
		detailsTitle: 'Definition Details',
		detailsSubtitle: 'Edit the description and other definition-wide settings.',
		closeConfirmation: 'Close confirmation',
		closeDefinitionDetails: 'Close definition details',
		closeRoundEditor: 'Close round editor',
		closeDisplayPreview: 'Close display preview',
		closeShortcutHelp: 'Close shortcut help',
		closeStepTemplatePicker: 'Close step template picker',
		description: 'Description',
		descriptionPlaceholder: 'What kind of experience should hosts expect?',
		showAdvanced: 'Show Advanced',
		hideAdvanced: 'Hide Advanced',
		definitionId: 'Definition id',
		definitionIdFixed: 'Definition id is fixed after creation',
		roundName: 'Round name',
		roundTitlePlaceholder: 'Round title',
		roundId: 'Round id',
		displayPreview: 'Display Preview',
		displayPreviewHelp: 'This uses the same big-screen step renderer as the live host display.',
		bigScreenPreview: 'Big Screen Preview',
		editorShortcuts: 'Editor Shortcuts',
		editorShortcutsHelp: 'These shortcuts work while the definition editor is active.',
		stepSorter: 'Step Sorter',
		stepSorterHelp: 'Drag slides to change the order or move them between rounds.',
		noStepsInRound:
			'No steps in this round yet. Drop one here or use New Step while this round is selected.',
		newRound: 'New Round',
		newStep: 'New Step',
		definitionDetails: 'Definition Details',
		saving: 'Saving...',
		chooseStepType: 'Choose A Step Type',
		chooseStepTypeHelp: 'Start with a question layout that matches how this slide should play.',
		mainScreen: 'Main Screen',
		mainScreenHelp:
			'Everything the audience sees first: question text, supporting copy, and media.',
		stepTitle: 'Title',
		stepTitlePlaceholder: 'Question title',
		body: 'Body',
		bodyPlaceholder: 'Optional supporting text on the big screen',
		stepId: 'Step id',
		questionMedia: 'Question media',
		questionMediaHelp:
			'Add an image, audio clip, or video to support the question on the main screen.',
		mediaTypeImageHelp: 'Reveal a still image on the main screen.',
		mediaTypeAudioHelp: 'Play an audio clue or sound effect.',
		mediaTypeVideoHelp: 'Show a video clip during the step.',
		removeMedia: 'Remove Media',
		addMedia: 'Add Media',
		loopMedia: 'Loop media',
		loopMediaHelp: 'Useful for short ambient clips and repeatable audio.',
		sourceUrl: 'Source URL',
		sourceUrlPlaceholder: '/api/v1/media/...',
		videoSourceUrlPlaceholder: '/api/v1/media/... or https://youtu.be/...',
		videoSourceHelp: 'Use a direct video URL, an uploaded file, or a YouTube link.',
		uploadFile: 'Upload file',
		uploadingMedia: 'Uploading media...',
		previewHelp: 'Add a media URL or upload a file to preview it here.',
		zoomStart: 'Start zoom',
		zoomStartHelp: 'Optional zoom level to begin from before the image pulls back.',
		zoomOriginX: 'Zoom focus X',
		zoomOriginXHelp: 'Optional horizontal focus point as a percentage from the left.',
		zoomOriginY: 'Zoom focus Y',
		zoomOriginYHelp: 'Optional vertical focus point as a percentage from the top.',
		zoomFocusPreviewHelp: 'Click the preview to place the zoom focus point.',
		resetZoomDefaults: 'Use default zoom',
		zoomFocusPreviewCaption:
			'The marker shows the zoom focal point used at the start of the reveal.',
		howPlayersAnswer: 'How Players Answer',
		howPlayersAnswerHelp:
			'Choose the interaction first, then configure the prompt and any options players will see.',
		recommendedScoring: 'Recommended scoring',
		inputPrompt: 'Input prompt',
		inputPromptPlaceholder: 'What should players do?',
		placeholder: 'Placeholder',
		placeholderHelp: 'Optional helper text inside the input',
		minValue: 'Min value',
		maxValue: 'Max value',
		sliderStep: 'Slider step',
		itemsToOrder: 'Items to order',
		answerChoices: 'Answer choices',
		selectableAnswers: 'Selectable answers',
		itemsToOrderHelp: 'These are the items players will arrange.',
		selectableAnswersHelp: 'These are the options players can choose from.',
		addOption: 'Add Option',
		correct: 'Correct',
		removeOption: 'Remove',
		points: 'Points',
		scoringAndCorrectAnswer: 'Scoring & Correct Answer',
		scoringHelp: 'Choose how this step awards points and what counts as correct.',
		correctOrderHelp: 'Set the correct order players should end up with.',
		correctNumber: 'Correct number',
		correctAnswerRubric: 'Correct answer / rubric',
		configurePointsAboveHelp:
			'Each checked option awards its configured points. Negative values subtract points.',
		hostReviewedHelp:
			'Submissions are reviewed by the host during the game. Add an optional correct answer or rubric to show on the host screen.',
		displayOnlyHelp: 'This step is display-only or reviewed outside the automatic scoring flow.',
		scoringSummary: 'Scoring summary',
		exactNumberSummary: 'Only the exact number scores.',
		closestNumberSummary: 'Nearest numeric answer wins the points.',
		configureScoresAbove: 'Configure scores in the option list above',
		configureScoresAboveHelp:
			'Each selected option can add or subtract points when players submit.',
		markCorrectOption: 'Mark the correct option in the answer list',
		markCorrectOptionHelp: 'Use the “Correct” radio control beside the right answer choice.',
		hostDecidesCorrectness: 'Host decides correctness live',
		hostDecidesCorrectnessHelp:
			'Use this when answers are subjective or spoken aloud instead of auto-checked.',
		expectedAnswer: 'Expected answer',
		expectedAnswerPlaceholder: 'Enter the expected answer',
		noAnswerRequired: 'No answer required',
		noAnswerRequiredHelp: 'Use this for reveal-only slides or host-led moments.',
		timer: 'Timer',
		timerHelp:
			'Set the pace of the question and decide whether the step should close automatically.',
		timerSeconds: 'Timer seconds',
		durationSeconds: 'Duration (seconds)',
		enforcedTimer: 'Enforced timer',
		enforcedTimerHelp: 'Automatically close the step when the countdown reaches zero.',
		hostControls: 'Host Controls',
		hostControlsHelp:
			'Decide what the host can reveal and how much manual control they keep during play.',
		revealAnswers: 'Reveal answers',
		revealAnswersHelp: 'Allow the host to reveal the answer on screen.',
		showSubmissions: 'Show submissions',
		showSubmissionsHelp: 'Let the host inspect player answers live.',
		customPoints: 'Custom points',
		customPointsHelp: 'Allow the host to award a custom score during review.',
		sectionNavigation: [
			{ id: 'main-screen', label: 'Main Screen', icon: 'fluent:desktop-16-filled' },
			{
				id: 'player-answer',
				label: 'How Players Answer',
				icon: 'fluent:people-community-16-filled'
			},
			{ id: 'scoring', label: 'Scoring', icon: 'fluent:checkmark-circle-16-filled' },
			{ id: 'timer', label: 'Timer', icon: 'fluent:timer-16-filled' },
			{ id: 'host-controls', label: 'Host Controls', icon: 'fluent:person-settings-16-filled' }
		],
		shortcutGroups: [
			{
				title: 'Navigation',
				items: [
					{ keys: 'Alt + ArrowUp', label: 'Previous Step' },
					{ keys: 'Alt + ArrowDown', label: 'Next Step' }
				]
			},
			{
				title: 'Editing',
				items: [
					{ keys: 'Cmd/Ctrl + S', label: 'Save Definition' },
					{ keys: 'Cmd/Ctrl + Shift + A', label: 'Add Step After' },
					{ keys: 'Cmd/Ctrl + ,', label: 'Toggle Advanced Fields' },
					{ keys: 'Cmd/Ctrl + Backspace/Delete', label: 'Delete Step' }
				]
			},
			{
				title: 'View',
				items: [
					{ keys: 'Cmd/Ctrl + Shift + P', label: 'Preview' },
					{ keys: '?', label: 'Open Shortcut Help' }
				]
			}
		],
		headerActionLabels: {
			previousStep: 'Previous Step',
			nextStep: 'Next Step',
			deleteStep: 'Delete Step',
			shortcuts: 'Shortcuts',
			addStepAfter: 'Add Step After'
		},
		templateMeta: {
			trivia: {
				label: 'Trivia',
				description: 'Classic one-correct-answer multiple-choice question.',
				prompt: 'Pick the correct answer',
				options: ['Option 1', 'Option 2', 'Option 3', 'Option 4']
			},
			multiple_choice: {
				label: 'Multiple Choice',
				description: 'Select one or more answers with per-option scoring.',
				prompt: 'Select all that apply',
				options: ['Option 1', 'Option 2', 'Option 3', 'Option 4']
			},
			closest_guess: {
				label: 'Closest Guess',
				description: 'Players estimate a number and nearest answer wins.',
				prompt: 'Enter your best guess',
				placeholder: '0'
			},
			exact_number: {
				label: 'Exact Number',
				description: 'Only the exact numeric answer scores.',
				prompt: 'Enter the exact number',
				placeholder: '0'
			},
			ordering: {
				label: 'Ordering',
				description: 'Players must arrange items into the correct order.',
				prompt: 'Arrange these in the correct order',
				options: ['Item 1', 'Item 2', 'Item 3']
			},
			open_answer: {
				label: 'Open Answer',
				description: 'Players type a short answer that is checked exactly.',
				prompt: 'Type your answer',
				placeholder: 'Enter answer'
			},
			host_judged: {
				label: 'Host Judged',
				description: 'Collect answers and let the host review them live.',
				prompt: 'Type your answer',
				placeholder: 'Enter answer'
			},
			buzzer: {
				label: 'Buzzer',
				description: 'Fastest player buzzes in and answers verbally.',
				prompt: 'Buzz in when ready'
			},
			blank: {
				label: 'Blank',
				description: 'Start from a safe default and customize everything yourself.',
				prompt: '',
				placeholder: ''
			}
		},
		inputKinds: {
			text: {
				label: 'Free Text',
				description: 'Players type a written answer in their own words.'
			},
			number: {
				label: 'Number Guess',
				description: 'Players submit a number, either exact or closest wins.'
			},
			ordering: {
				label: 'Order Items',
				description: 'Players arrange items into the right sequence.'
			},
			radio: {
				label: 'Single Choice',
				description: 'Players pick one option from a list.'
			},
			checkbox: {
				label: 'Multiple Choice',
				description: 'Players can select several options, with optional weighting.'
			},
			buzzer: {
				label: 'Buzzer',
				description: 'Players race to buzz in before answering live.'
			},
			none: {
				label: 'No Player Input',
				description: 'Use the slide for reveal-only or host-led moments.'
			}
		},
		evaluations: {
			none: {
				label: 'No Scoring',
				description: 'Show the question without collecting or grading player answers.'
			},
			host_judged: {
				label: 'Host Judged',
				description: 'The host decides whether answers are correct during play.'
			},
			exact_text: {
				label: 'Exact Match',
				description: 'Players must match the expected answer exactly.'
			},
			exact_number: {
				label: 'Exact Number',
				description: 'Only the precise numeric answer scores.'
			},
			closest_number: {
				label: 'Closest Wins',
				description: 'Nearest number gets the points.'
			},
			ordering_match: {
				label: 'Correct Order',
				description: 'Players score by matching the intended sequence.'
			},
			multi_select_weighted: {
				label: 'Weighted Choices',
				description: 'Each selected option adds or subtracts points.'
			}
		},
		health: {
			missingTitle: 'Title missing',
			missingOptions: 'Needs at least 2 options',
			missingAnswer: 'Correct answer missing',
			hostlessSkipped: 'Hostless games will skip this step',
			hostlessMissingAnswer:
				'Hostless games will skip this step because it has no auto-evaluable answer',
			hostlessCheckboxReview:
				'Hostless games will skip checkbox steps that still require host review',
			missingMedia: 'Media source missing',
			missingTimer: 'Timer not set'
		},
		imageReveal: {
			none: { label: 'none', description: 'Show the image as-is.' },
			blur_to_clear: {
				label: 'blur to clear',
				description: 'Start blurred and sharpen over time.'
			},
			blur_circle: {
				label: 'blur circle',
				description: 'Reveal the image through a moving spotlight.'
			},
			zoom_out: { label: 'zoom out', description: 'Start zoomed in and pull back.' }
		},
		previewFallback: 'No supporting text yet.',
		slide: 'Slide',
		untitledStep: 'Untitled step',
		deleteRoundTitle: (label: string) => `Delete ${label}?`,
		deleteRoundMessage: 'This round and all of its steps will be removed from the definition.',
		deleteRoundConfirm: 'Delete Round',
		deleteStepTitle: (label: string) => `Delete ${label}?`,
		deleteStepMessage:
			'This step will be removed from the definition and cannot be recovered from the editor.',
		deleteStepConfirm: 'Delete Step'
	},
	error: {
		pageTitle: 'Error',
		message: (status: number, detail: string) => `${status}: ${detail}`
	}
} as const);

type Messages = typeof en;

const et: Messages = {
	common: {
		appName: 'Peomäng',
		language: 'Keel',
		home: 'Avaleht',
		back: 'Tagasi',
		cancel: 'Loobu',
		close: 'Sulge',
		save: 'Salvesta',
		saveDetails: 'Salvesta detailid',
		saveRound: 'Salvesta voor',
		loading: 'Laadimine...',
		live: 'Otse',
		disconnected: 'Ühendus katkenud',
		on: 'Sees',
		off: 'Väljas',
		host: 'Mängujuht',
		manageDefinitions: 'Halda definitsioone',
		createGame: 'Loo mäng',
		createDefinition: 'Loo definitsioon',
		edit: 'Muuda',
		remove: 'Eemalda',
		add: 'Lisa',
		preview: 'Eelvaade',
		rounds: 'Voorud',
		steps: 'sammu',
		selected: 'Valitud',
		connection: 'Ühendus',
		question: 'Küsimus',
		answerReveal: 'Vastuse näitamine',
		nowPlaying: 'Praegu ekraanil',
		revealedAnswer: 'Näidatud vastus',
		correctAnswer: 'Õige vastus',
		waitingForNextQuestion: 'Ootab järgmist küsimust...',
		finalResult: 'Lõpptulemus',
		score: 'Skoor',
		pointsWord: 'punkti',
		breadcrumb: 'Leivapuru'
	},
	home: {
		title: 'Peomängu Areen',
		subtitle: 'Vali, kuidas soovid mängu siseneda.',
		create: 'Loo',
		join: 'Liitu'
	},
	create: {
		title: 'Loo mäng',
		subtitle: 'Vali definitsioon, vaata see üle ja otsusta, kas mängu juhib mängujuhi telefon.',
		gameDefinition: 'Mängu definitsioon',
		hostEnabledMode: 'Mängujuhiga režiim',
		hostEnabledHelp: 'Kui see on sees, saab esimesena liitunud mängijast mängujuhi kontroller.',
		definitionPreview: 'Definitsiooni eelvaade',
		loadingDefinitionDetails: 'Laen definitsiooni detaile...',
		noDefinitionSelected: 'Definitsiooni pole valitud.',
		noDescriptionProvided: 'Kirjeldus puudub.'
	},
	join: {
		title: 'Liitu mänguga',
		subtitle: 'Sea oma mängijaprofiil ja sisesta 5-täheline mängu kood.',
		avatar: 'Avatar',
		playerFallback: 'Mängija',
		customPhotoAvatar: 'Kohandatud fotoavatar',
		preset: 'Valmiskujundus',
		random: 'Juhuslik',
		hideAvatarOptions: 'Peida avatari valikud',
		changeAvatar: 'Puuduta avatari muutmiseks',
		name: 'Nimi',
		namePlaceholder: 'Sinu nimi',
		choosePresetAvatar: 'Vali valmisavatar',
		takePhotoOrChoose: 'Tee foto või vali olemasolev',
		photoHelp: 'Pilt lõigatakse enne üleslaadimist ruudukujuliseks 256x256 avatariks.',
		useCameraPhoto: 'Kasuta kaamerat / fotot',
		adjustPhoto: 'Lohista pilti paika ja kasuta suumi, et raamida oma avatar.',
		uploading: 'Laen üles...',
		useThisPhoto: 'Kasuta seda fotot',
		customAvatarReady: 'Kohandatud avatar on järgmiseks liitumiseks valmis.',
		joinCode: 'Liitumiskood',
		joinCodePlaceholder: 'ABCDE',
		checkingSavedAvatar: 'Kontrollin salvestatud kohandatud avatari...',
		couldNotJoinGame: 'Mänguga ei saanud liituda.',
		couldNotPrepareAvatar: 'Avatari pilti ei saanud ette valmistada.',
		couldNotUploadAvatar: 'Avatari ei saanud üles laadida.',
		joinAction: 'Liitu'
	},
	definitions: {
		title: 'Halda definitsioone',
		subtitle:
			'Vaata salvestatud mängudefinitsioone ja ava redaktor, kui soovid midagi luua või uuendada.',
		currentDefinitions: 'Praegused definitsioonid',
		noDefinitionsYet: 'Definitsioone veel pole',
		noDefinitionsHelp: 'Loo oma esimene definitsioon, et hakata voorusid ja slaide ehitama.',
		noDescriptionProvidedYet: 'Kirjeldust pole veel lisatud.',
		definitionBadge: 'Definitsioon',
		newDefinitionTitle: 'Uus definitsioon',
		editDefinitionTitle: 'Muuda definitsiooni',
		couldNotLoadDefinitions: 'Definitsioonide laadimine ebaõnnestus.',
		couldNotLoadDefinition: (definitionId) => `Definitsiooni "${definitionId}" ei saanud laadida.`,
		definitionSaved: 'Definitsioon salvestatud.',
		couldNotSaveDefinition: 'Definitsiooni ei saanud salvestada.',
		untitledDefinition: 'Pealkirjata definitsioon',
		newDefinitionBreadcrumb: 'Uus definitsioon',
		editDefinitionBreadcrumb: 'Muuda definitsiooni'
	},
	hostView: {
		hostLobbyTitle: 'Mängujuhi lobby',
		joinCode: 'Liitumiskood',
		hostMode: 'Mängujuhi režiim',
		useHostController: 'Kasuta mängujuhi kontrollerit mängu käivitamiseks ja juhtimiseks.',
		finalResultsReady:
			'Lõpptulemused on valmis. Näita finaali mängujuhi kontrollerist siis, kui oled valmis.',
		playerStatusWaiting: 'Ootab mängijaid'
	},
	gameplay: {
		hostControllerTitle: 'Mängujuhi kontroller',
		playerControllerTitle: 'Mängija kontroller',
		waitingForGameStart: 'Mängu algust oodatakse.',
		youAreHostController: 'Sina oled mängujuhi kontroller.',
		youCanStartAsFirstPlayer: 'Liitusid esimesena, seega saad selle mängujuhita mängu käivitada.',
		youCanContinueInfoSlide: 'Liitusid esimesena, seega saad selle infoliuguri edasi viia.',
		startGame: 'Alusta mängu',
		finaleControls: 'Finaali juhtimine',
		stage: 'Etapp',
		autoplay: 'Automaatesitus',
		resetToPodium: 'Lähtesta poodiumile',
		nextFinaleStage: 'Järgmine finaalietapp',
		disableAutoplay: 'Lülita automaatesitus välja',
		enableAutoplay: 'Lülita automaatesitus sisse',
		buzzer: 'Summer',
		answerReceivedWaiting: 'Vastus käes. Ootame järgmist sammu.',
		stepClosed: 'See samm on suletud.',
		buzzerChanceUsed: 'Oled selle küsimuse summeri võimaluse juba kasutanud.',
		buzzNow: 'Vajuta nüüd!',
		waitForHost: 'Oota, kuni mängujuht jätkab.',
		yourAnswer: 'Sinu vastus',
		answerSubmitted: 'Sinu vastus on kohal. Järgmisel sammul saad uuesti vastata.',
		stepClosedAnswersDisabled: 'See samm on suletud. Uusi vastuseid ei saa sisestada.',
		typeYourAnswer: 'Kirjuta oma vastus',
		enterNumber: 'Sisesta number',
		submitAnswer: 'Saada vastus',
		orderingAnswer: 'Järjestusvastus',
		orderSubmitted: 'Sinu järjestus on saadetud. Järgmisel sammul saad uuesti järjestada.',
		reorderingDisabled: 'See samm on suletud. Ümberjärjestamine on keelatud.',
		dragItemsToOrder: 'Lohista elemendid soovitud järjekorda ja saada seejärel vastus.',
		submitOrder: 'Saada järjestus',
		chooseOne: 'Vali üks',
		choiceLocked: 'Sinu valik on lukustatud. Järgmisel sammul saad uuesti valida.',
		newSelectionsDisabled: 'See samm on suletud. Uued valikud on keelatud.',
		tapOneOption: 'Puuduta ühte valikut, et see kohe saata.',
		chooseOneOrMore: 'Vali üks või mitu',
		selectionSubmitted: 'Sinu valik on saadetud. Järgmisel sammul saad uuesti valida.',
		tapOptionsThenSubmit: 'Puuduta valikuid nende märkimiseks ja saada siis, kui oled valmis.',
		submitSelection: 'Saada valik',
		noPhoneInput: 'Selles sammus ei ole telefoni sisendit vaja.',
		gameComplete: 'Mäng on lõppenud.',
		scoreboardShowingOnMainScreen: 'Tabel on praegu põhiekraanil nähtav.',
		revealFinaleFromHost: 'Kasuta all olevat mängujuhi kontrollerit finaalivaate näitamiseks.',
		waitingForFinalResults: 'Ootan, kuni host näitab lõpptulemusi.',
		revealFinale: 'Näita finaali',
		gameFinishedRevealEndScreen: 'Mäng on lõppenud. Näita lõppvaadet siis, kui oled valmis.',
		hostControls: 'Mängujuhi kontrollid',
		phaseLabel: 'Faas',
		submissionsLabel: 'Vastuseid',
		pendingReviewLabel: 'Ootab ülevaatust',
		answered: 'vastas',
		previous: 'Eelmine',
		advanceStep: 'Liigu edasi',
		next: 'Järgmine',
		showAnswer: 'Näita vastust',
		resetQuestion: 'Lähtesta küsimus',
		hideScoreboard: 'Peida tabel',
		showScoreboard: 'Näita tabelit',
		videoPlayback: 'Video taasesitus',
		pauseMedia: 'Peata video',
		resumeMedia: 'Jätka videot',
		autoEvaluate: 'Hinda automaatselt',
		disableBuzzer: 'Keela summer',
		enableEligibleBuzzers: 'Luba sobivad summerid',
		reviewQueue: 'Ülevaatamise järjekord',
		buzzedInFirst: 'Vajutas esimesena',
		acceptWithPoints: (points) => `Kinnita +${points}`,
		reject: 'Lükka tagasi',
		waitingToReactivateBuzzers: 'Ootan, kuni host lubab sobivad summerid uuesti.',
		lockedOut: 'Lukustatud välja',
		noAnswersSubmittedYet: 'Ühtegi vastust pole veel saadetud.',
		reveal: 'Näita',
		reviewed: 'Üle vaadatud',
		acceptCustomPoints: (points) => `Kinnita ${points > 0 ? '+' : ''}${points}`,
		manualScore: 'Käsitsi skoor',
		reactionBarTitle: 'Reaktsioonid',
		reactionBarHelp: 'Puuduta kiiresti, et saata lõbusaid reaktsioone põhiekraanile.',
		reactionBurstOverlayLabel: 'Reaalajas publiku reaktsioonid',
		reactionLabels: {
			laugh: 'Naerureaktsioon',
			fire: 'Tule reaktsioon',
			clap: 'Aplausireaktsioon',
			shock: 'Üllatusreaktsioon',
			poop: 'Kaka reaktsioon',
			vomit: 'Oksereaktsioon'
		}
	},
	timer: {
		timeRemaining: 'Aega järel',
		timerEnforced: 'Taimer on kohustuslik',
		timerAdvisory: 'Taimer on soovituslik'
	},
	finale: {
		title: 'Lõpptulemused',
		thirdPlaceReveal: 'Kolmanda koha avalikustamine',
		secondPlaceReveal: 'Teise koha avalikustamine',
		firstPlaceReveal: 'Võitja avalikustamine',
		bestMoments: 'Mängu parimad hetked',
		fullScoreboard: 'Täielik lõpptabel',
		noFinalStandingsYet: 'Lõppjärjestust veel pole.',
		place: (place) => `Koht #${place}`,
		stageLabel: (stage): string =>
			stage === 'third_place'
				? 'Kolmas koht'
				: stage === 'second_place'
					? 'Teine koht'
					: stage === 'first_place'
						? 'Esimene koht'
						: stage === 'stats'
							? 'Statistika'
							: 'Tabel',
		noStatsYet: 'Statistikat veel pole',
		noStatsHelp: 'See mäng ei andnud finaali tipphetkedeks piisavalt andmeid.',
		finished: 'Lõpetatud',
		gameComplete: 'Mäng lõppenud',
		youWonTheGame: 'Sa võitsid mängu',
		topThreeFinish: 'Koht esikolmikus',
		finalStandingsIn: 'Lõppjärjestus on teada',
		notIncludedInStandings: 'Sinu kontroller on ühendatud, kuid sind ei kaasatud lõppjärjestusse.'
	},
	editor: {
		detailsTitle: 'Definitsiooni detailid',
		detailsSubtitle: 'Muuda kirjeldust ja teisi definitsiooni üldseadeid.',
		closeConfirmation: 'Sulge kinnitus',
		closeDefinitionDetails: 'Sulge definitsiooni detailid',
		closeRoundEditor: 'Sulge vooru muutmine',
		closeDisplayPreview: 'Sulge ekraani eelvaade',
		closeShortcutHelp: 'Sulge otseteede abi',
		closeStepTemplatePicker: 'Sulge sammutüübi valik',
		description: 'Kirjeldus',
		descriptionPlaceholder: 'Millist kogemust võiks mängujuht sellest oodata?',
		showAdvanced: 'Näita täpsemaid valikuid',
		hideAdvanced: 'Peida täpsemad valikud',
		definitionId: 'Definitsiooni id',
		definitionIdFixed: 'Definitsiooni id on pärast loomist fikseeritud',
		roundName: 'Vooru nimi',
		roundTitlePlaceholder: 'Vooru pealkiri',
		roundId: 'Vooru id',
		displayPreview: 'Ekraani eelvaade',
		displayPreviewHelp:
			'See kasutab sama suure ekraani sammurenderdajat nagu päris mängujuhi vaade.',
		bigScreenPreview: 'Suure ekraani eelvaade',
		editorShortcuts: 'Redaktori otseteed',
		editorShortcutsHelp: 'Need otseteed töötavad siis, kui definitsiooni redaktor on aktiivne.',
		stepSorter: 'Sammude järjestaja',
		stepSorterHelp: 'Lohista slaide järjekorra muutmiseks või teise vooru viimiseks.',
		noStepsInRound:
			'Selles voorus pole veel samme. Lohista üks siia või kasuta valikut Uus samm, kui see voor on valitud.',
		newRound: 'Uus voor',
		newStep: 'Uus samm',
		definitionDetails: 'Definitsiooni detailid',
		saving: 'Salvestan...',
		chooseStepType: 'Vali sammu tüüp',
		chooseStepTypeHelp: 'Alusta küsimuse paigutusega, mis sobib selle slaidi mänguloogikaga.',
		mainScreen: 'Põhiekraan',
		mainScreenHelp: 'Kõik, mida publik esimesena näeb: küsimuse tekst, toetav sisu ja meedia.',
		stepTitle: 'Pealkiri',
		stepTitlePlaceholder: 'Küsimuse pealkiri',
		body: 'Sisu',
		bodyPlaceholder: 'Valikuline toetav tekst suurele ekraanile',
		stepId: 'Sammu id',
		questionMedia: 'Küsimuse meedia',
		questionMediaHelp: 'Lisa pilt, heliklipp või video, mis toetab põhiekraani küsimust.',
		mediaTypeImageHelp: 'Näita põhiekraanil staatilist pilti.',
		mediaTypeAudioHelp: 'Mängi helivihjet või heliefekti.',
		mediaTypeVideoHelp: 'Näita sammu ajal videoklippi.',
		removeMedia: 'Eemalda meedia',
		addMedia: 'Lisa meedia',
		loopMedia: 'Korda meediat',
		loopMediaHelp: 'Kasulik lühikeste taustaklippide ja korduva heli jaoks.',
		sourceUrl: 'Allika URL',
		sourceUrlPlaceholder: '/api/v1/media/...',
		videoSourceUrlPlaceholder: '/api/v1/media/... või https://youtu.be/...',
		videoSourceHelp: 'Kasuta otsest videolinki, üles laaditud faili või YouTube linki.',
		uploadFile: 'Laadi fail üles',
		uploadingMedia: 'Meediat laaditakse üles...',
		previewHelp: 'Lisa meedia URL või laadi fail üles, et näha siin eelvaadet.',
		zoomStart: 'Algsuum',
		zoomStartHelp: 'Valikuline suumitase, millest pilt enne eemaldumist algab.',
		zoomOriginX: 'Suumi fookus X',
		zoomOriginXHelp: 'Valikuline horisontaalne fookuspunkt protsendina vasakust servast.',
		zoomOriginY: 'Suumi fookus Y',
		zoomOriginYHelp: 'Valikuline vertikaalne fookuspunkt protsendina ülemisest servast.',
		zoomFocusPreviewHelp: 'Klõpsa eelvaatel, et määrata suumi fookuspunkt.',
		resetZoomDefaults: 'Kasuta vaikimisi suumi',
		zoomFocusPreviewCaption:
			'Marker näitab suumi fookuspunkti, mida kasutatakse paljastuse alguses.',
		howPlayersAnswer: 'Kuidas mängijad vastavad',
		howPlayersAnswerHelp:
			'Vali esmalt suhtlusviis ja seejärel seadista küsimus ning võimalikud valikud.',
		recommendedScoring: 'Soovitatud hindamine',
		inputPrompt: 'Sisendi juhis',
		inputPromptPlaceholder: 'Mida mängijad tegema peaksid?',
		placeholder: 'Kohthoidja',
		placeholderHelp: 'Valikuline abitekst sisendvälja sees',
		minValue: 'Min väärtus',
		maxValue: 'Maks väärtus',
		sliderStep: 'Liuguri samm',
		itemsToOrder: 'Järjestatavad elemendid',
		answerChoices: 'Vastusvariandid',
		selectableAnswers: 'Valitavad vastused',
		itemsToOrderHelp: 'Need on elemendid, mida mängijad järjestavad.',
		selectableAnswersHelp: 'Need on valikud, mille seast mängijad saavad valida.',
		addOption: 'Lisa valik',
		correct: 'Õige',
		removeOption: 'Eemalda',
		points: 'Punktid',
		scoringAndCorrectAnswer: 'Punktid ja õige vastus',
		scoringHelp: 'Vali, kuidas see samm punkte annab ja mis loetakse õigeks.',
		correctOrderHelp: 'Määra õige järjestus, milleni mängijad peaksid jõudma.',
		correctNumber: 'Õige number',
		correctAnswerRubric: 'Õige vastus / hindamisreegel',
		configurePointsAboveHelp:
			'Iga märgitud valik annab oma punktid. Negatiivsed väärtused lahutavad punkte.',
		hostReviewedHelp:
			'Mängujuht vaatab vastused mängu ajal üle. Soovi korral lisa õige vastus või hindamisreegel, mida mängujuhile näidata.',
		displayOnlyHelp:
			'See samm on ainult näitamiseks või vaadatakse üle väljaspool automaatset hindamist.',
		scoringSummary: 'Punktide kokkuvõte',
		exactNumberSummary: 'Punkte annab ainult täpne number.',
		closestNumberSummary: 'Punktid saab lähim arvuline vastus.',
		configureScoresAbove: 'Seadista punktid ülal olevas valikute loendis',
		configureScoresAboveHelp:
			'Iga valitud vastus võib mängijate esitamisel punkte lisada või maha võtta.',
		markCorrectOption: 'Märgi vastuseloendis õige valik',
		markCorrectOptionHelp: 'Kasuta õige vastuse kõrval olevat raadionuppu „Õige”.',
		hostDecidesCorrectness: 'Mängujuht otsustab õigsuse jooksvalt',
		hostDecidesCorrectnessHelp:
			'Kasuta seda siis, kui vastused on subjektiivsed või öeldakse valjult välja.',
		expectedAnswer: 'Oodatud vastus',
		expectedAnswerPlaceholder: 'Sisesta oodatud vastus',
		noAnswerRequired: 'Vastust pole vaja',
		noAnswerRequiredHelp: 'Kasuta seda paljastusslaidide või mängujuhi juhitud hetkede jaoks.',
		timer: 'Taimer',
		timerHelp: 'Määra küsimuse tempo ja otsusta, kas samm peaks automaatselt sulguma.',
		timerSeconds: 'Taimeri sekundid',
		durationSeconds: 'Kestus (sekundites)',
		enforcedTimer: 'Sunnitud taimer',
		enforcedTimerHelp: 'Sulge samm automaatselt, kui loendus jõuab nulli.',
		hostControls: 'Mängujuhi kontrollid',
		hostControlsHelp:
			'Otsusta, mida mängujuht saab näidata ja kui palju käsitsi juhtimist talle jääb.',
		revealAnswers: 'Näita vastuseid',
		revealAnswersHelp: 'Luba mängujuhil ekraanil õige vastus välja tuua.',
		showSubmissions: 'Näita vastuseid',
		showSubmissionsHelp: 'Luba mängujuhil mängijate vastuseid mängu ajal vaadata.',
		customPoints: 'Kohandatud punktid',
		customPointsHelp: 'Luba mängujuhil ülevaatuse ajal käsitsi punktisummat muuta.',
		sectionNavigation: [
			{ id: 'main-screen', label: 'Põhiekraan', icon: 'fluent:desktop-16-filled' },
			{
				id: 'player-answer',
				label: 'Kuidas mängijad vastavad',
				icon: 'fluent:people-community-16-filled'
			},
			{ id: 'scoring', label: 'Punktiarvestus', icon: 'fluent:checkmark-circle-16-filled' },
			{ id: 'timer', label: 'Taimer', icon: 'fluent:timer-16-filled' },
			{
				id: 'host-controls',
				label: 'Mängujuhi nupud',
				icon: 'fluent:person-settings-16-filled'
			}
		],
		shortcutGroups: [
			{
				title: 'Liikumine',
				items: [
					{ keys: 'Alt + ArrowUp', label: 'Eelmine samm' },
					{ keys: 'Alt + ArrowDown', label: 'Järgmine samm' }
				]
			},
			{
				title: 'Muutmine',
				items: [
					{ keys: 'Cmd/Ctrl + S', label: 'Salvesta definitsioon' },
					{ keys: 'Cmd/Ctrl + Shift + A', label: 'Lisa samm järele' },
					{ keys: 'Cmd/Ctrl + ,', label: 'Lülita täpsemad väljad' },
					{ keys: 'Cmd/Ctrl + Backspace/Delete', label: 'Kustuta samm' }
				]
			},
			{
				title: 'Vaade',
				items: [
					{ keys: 'Cmd/Ctrl + Shift + P', label: 'Eelvaade' },
					{ keys: '?', label: 'Ava otseteede abi' }
				]
			}
		],
		headerActionLabels: {
			previousStep: 'Eelmine samm',
			nextStep: 'Järgmine samm',
			deleteStep: 'Kustuta samm',
			shortcuts: 'Otseteed',
			addStepAfter: 'Lisa samm järele'
		},
		templateMeta: {
			trivia: {
				label: 'Trivia',
				description: 'Klassikaline ühe õige vastusega valikvastuse küsimus.',
				prompt: 'Vali õige vastus',
				options: ['Valik 1', 'Valik 2', 'Valik 3', 'Valik 4']
			},
			multiple_choice: {
				label: 'Mitmikvalik',
				description: 'Vali üks või mitu vastust koos punktidega valiku kaupa.',
				prompt: 'Vali kõik sobivad',
				options: ['Valik 1', 'Valik 2', 'Valik 3', 'Valik 4']
			},
			closest_guess: {
				label: 'Lähim pakkumine',
				description: 'Mängijad hindavad arvu ja lähim vastus võidab.',
				prompt: 'Sisesta oma parim pakkumine',
				placeholder: '0'
			},
			exact_number: {
				label: 'Täpne number',
				description: 'Punkte annab ainult täpne arvuline vastus.',
				prompt: 'Sisesta täpne number',
				placeholder: '0'
			},
			ordering: {
				label: 'Järjestamine',
				description: 'Mängijad peavad elemendid õigesse järjekorda seadma.',
				prompt: 'Sea need õigesse järjekorda',
				options: ['Element 1', 'Element 2', 'Element 3']
			},
			open_answer: {
				label: 'Avatud vastus',
				description: 'Mängijad kirjutavad lühivastuse, mida kontrollitakse täpselt.',
				prompt: 'Kirjuta oma vastus',
				placeholder: 'Sisesta vastus'
			},
			host_judged: {
				label: 'Mängujuht hindab',
				description: 'Kogu vastused ja lase mängujuhil need mängu ajal üle vaadata.',
				prompt: 'Kirjuta oma vastus',
				placeholder: 'Sisesta vastus'
			},
			buzzer: {
				label: 'Summer',
				description: 'Kiireim mängija vajutab ja vastab suuliselt.',
				prompt: 'Vajuta, kui oled valmis'
			},
			blank: {
				label: 'Tühi',
				description: 'Alusta turvalise vaikeseadega ja kohanda kõike ise.',
				prompt: '',
				placeholder: ''
			}
		},
		inputKinds: {
			text: {
				label: 'Vabatekst',
				description: 'Mängijad kirjutavad vastuse oma sõnadega.'
			},
			number: {
				label: 'Arvupakkumine',
				description: 'Mängijad saadavad numbri; võidab täpne või lähim.'
			},
			ordering: {
				label: 'Järjesta elemendid',
				description: 'Mängijad panevad elemendid õigesse järjestusse.'
			},
			radio: {
				label: 'Üks valik',
				description: 'Mängijad valivad loendist ühe vastuse.'
			},
			checkbox: {
				label: 'Mitmikvalik',
				description: 'Mängijad saavad valida mitu vastust, koos punktikaaludega.'
			},
			buzzer: {
				label: 'Summer',
				description: 'Mängijad võistlevad, et esimesena vajutada ja vastata.'
			},
			none: {
				label: 'Mängija sisend puudub',
				description: 'Kasuta slaidi ainult paljastuseks või mängujuhi juhitud hetkeks.'
			}
		},
		evaluations: {
			none: {
				label: 'Punkte ei jagata',
				description: 'Näita küsimust ilma mängijate vastuseid kogumata või hindamata.'
			},
			host_judged: {
				label: 'Mängujuht hindab',
				description: 'Mängujuht otsustab mängu ajal, kas vastused on õiged.'
			},
			exact_text: {
				label: 'Täielik vaste',
				description: 'Mängijad peavad oodatud vastusega täpselt kattuma.'
			},
			exact_number: {
				label: 'Täpne number',
				description: 'Punkte annab ainult täpne arvuline vastus.'
			},
			closest_number: {
				label: 'Lähim võidab',
				description: 'Punktid saab lähim arv.'
			},
			ordering_match: {
				label: 'Õige järjekord',
				description: 'Mängijad teenivad punkte, kui tabavad õige järjestuse.'
			},
			multi_select_weighted: {
				label: 'Kaalutud valikud',
				description: 'Iga valitud vastus lisab või lahutab punkte.'
			}
		},
		health: {
			missingTitle: 'Pealkiri puudub',
			missingOptions: 'Vähemalt 2 valikut on vaja',
			missingAnswer: 'Õige vastus puudub',
			hostlessSkipped: 'Mängujuhita mäng jätab selle sammu vahele',
			hostlessMissingAnswer:
				'Mängujuhita mäng jätab selle sammu vahele, sest seda ei saa vastuse põhjal automaatselt hinnata',
			hostlessCheckboxReview:
				'Mängujuhita mäng jätab summerivabad märkeruudusammud vahele, kui need vajavad endiselt käsitsi ülevaatust',
			missingMedia: 'Meedia allikas puudub',
			missingTimer: 'Taimer pole määratud'
		},
		imageReveal: {
			none: { label: 'puudub', description: 'Näita pilti muutmata kujul.' },
			blur_to_clear: {
				label: 'hägusast selgeks',
				description: 'Alusta häguselt ja tee pilt aja jooksul selgemaks.'
			},
			blur_circle: {
				label: 'hägus ring',
				description: 'Paljasta pilt liikuva valguslaigu kaudu.'
			},
			zoom_out: { label: 'välja suumimine', description: 'Alusta lähedalt ja tõmba tagasi.' }
		},
		previewFallback: 'Toetavat teksti veel pole.',
		slide: 'Slaid',
		untitledStep: 'Pealkirjata samm',
		deleteRoundTitle: (label) => `Kustuta ${label}?`,
		deleteRoundMessage: 'See voor ja kõik selle sammud eemaldatakse definitsioonist.',
		deleteRoundConfirm: 'Kustuta voor',
		deleteStepTitle: (label) => `Kustuta ${label}?`,
		deleteStepMessage: 'See samm eemaldatakse definitsioonist ja seda ei saa redaktoris taastada.',
		deleteStepConfirm: 'Kustuta samm'
	},
	error: {
		pageTitle: 'Viga',
		message: (status, detail) => `${status}: ${detail}`
	}
};

const translations = {
	en,
	et
} satisfies Record<Locale, Messages>;

export const locale = createLocalStorageStore<Locale>('partygame-locale', fallbackLocale);

export const messages = derived(
	locale,
	($locale) => translations[$locale] ?? translations[fallbackLocale]
);

export function getMessages(localeCode?: Locale): Messages {
	return localeCode ? (translations[localeCode] ?? translations[fallbackLocale]) : get(messages);
}

export function pageTitle(title?: string): string {
	const appName = getMessages().common.appName;
	return title ? `${title} | ${appName}` : appName;
}

export function connectionLabel(connected: boolean): string {
	const common = getMessages().common;
	return connected ? common.live : common.disconnected;
}

export function onOffLabel(value: boolean): string {
	const common = getMessages().common;
	return value ? common.on : common.off;
}

export function formatPlayerStatus(status: string): string {
	const common = getMessages().common;
	if (status === 'connected') {
		return common.live;
	}
	if (status === 'disconnected') {
		return common.disconnected;
	}
	return status;
}

export function formatPhaseLabel(phase: string): string {
	const gameplay = getMessages().gameplay;
	const labels: Record<string, string> = {
		waiting_for_players: getMessages().hostView.playerStatusWaiting,
		waiting: getMessages().hostView.playerStatusWaiting,
		question_active: gameplay.next,
		host_review: gameplay.reviewQueue,
		answer_reveal: getMessages().common.answerReveal,
		finished: gameplay.gameComplete
	};
	return labels[phase] ?? phase;
}

export function formatSeconds(value: number): string {
	return `${value}s`;
}

export function formatScoreDelta(points: number): string {
	return `${points > 0 ? '+' : ''}${points}`;
}
