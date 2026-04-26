import type { Messages } from '$lib/i18n';

export type StepSelectionSnapshot = {
	stepId?: string;
	roundIndex: number;
	stepIndex: number;
} | null;

export type DefinitionHistoryEntry = {
	before: string;
	after: string;
	description: string;
	createdAt: number;
	selectionBefore: StepSelectionSnapshot;
	selectionAfter: StepSelectionSnapshot;
};

export type DefinitionHistoryState = {
	undoStack: DefinitionHistoryEntry[];
	redoStack: DefinitionHistoryEntry[];
	lastDraftSnapshot: string;
	lastSelectionSnapshot: StepSelectionSnapshot;
	ready: boolean;
	suppressNextChange: boolean;
};

type HistoryMessages = Messages['editor']['history'];

const HISTORY_LIMIT = 100;
const COALESCE_MS = 1000;

export function createDefinitionHistoryState(): DefinitionHistoryState {
	return {
		undoStack: [],
		redoStack: [],
		lastDraftSnapshot: '',
		lastSelectionSnapshot: null,
		ready: false,
		suppressNextChange: false
	};
}

export function serializeDefinition(definition: GameDefinition) {
	return JSON.stringify(definition);
}

export function resetDefinitionHistory(
	history: DefinitionHistoryState,
	definition: GameDefinition,
	selection: StepSelectionSnapshot
) {
	history.undoStack = [];
	history.redoStack = [];
	history.lastDraftSnapshot = serializeDefinition(definition);
	history.lastSelectionSnapshot = selection;
	history.ready = true;
	history.suppressNextChange = false;
}

export function recordDefinitionHistoryChange(
	history: DefinitionHistoryState,
	before: string,
	after: string,
	selectionBefore: StepSelectionSnapshot,
	selectionAfter: StepSelectionSnapshot,
	messages: HistoryMessages
) {
	const description = describeDefinitionChange(before, after, messages);
	const now = Date.now();
	const previousEntry = history.undoStack[history.undoStack.length - 1];
	if (
		previousEntry &&
		previousEntry.description === description &&
		now - previousEntry.createdAt < COALESCE_MS
	) {
		previousEntry.after = after;
		previousEntry.createdAt = now;
		previousEntry.selectionAfter = selectionAfter;
		history.undoStack = [...history.undoStack];
	} else {
		history.undoStack = [
			...history.undoStack,
			{
				before,
				after,
				description,
				createdAt: now,
				selectionBefore,
				selectionAfter
			}
		].slice(-HISTORY_LIMIT);
	}
	history.redoStack = [];
}

export function getUndoEntry(history: DefinitionHistoryState) {
	return history.undoStack[history.undoStack.length - 1] ?? null;
}

export function popUndoEntry(history: DefinitionHistoryState, entry: DefinitionHistoryEntry) {
	const latestEntry = getUndoEntry(history);
	if (
		!latestEntry ||
		latestEntry.before !== entry.before ||
		latestEntry.after !== entry.after ||
		latestEntry.createdAt !== entry.createdAt
	) {
		return false;
	}
	history.undoStack = history.undoStack.slice(0, -1);
	history.redoStack = [...history.redoStack, latestEntry];
	return true;
}

export function popRedoEntry(history: DefinitionHistoryState) {
	const entry = history.redoStack[history.redoStack.length - 1];
	if (!entry) {
		return null;
	}
	history.redoStack = history.redoStack.slice(0, -1);
	history.undoStack = [...history.undoStack, entry];
	return entry;
}

function stepLabel(
	step: StepDefinition | undefined,
	fallbackIndex: number,
	messages: HistoryMessages
) {
	return step?.title?.trim() || messages.fallbackStepLabel(fallbackIndex + 1);
}

function describeDefinitionChange(before: string, after: string, messages: HistoryMessages) {
	const beforeDefinition = JSON.parse(before) as GameDefinition;
	const afterDefinition = JSON.parse(after) as GameDefinition;
	if (beforeDefinition.title !== afterDefinition.title) {
		return messages.editedDefinitionTitle(beforeDefinition.title, afterDefinition.title);
	}
	if (beforeDefinition.description !== afterDefinition.description) {
		return messages.editedDefinitionDescription;
	}
	if (beforeDefinition.visibility !== afterDefinition.visibility) {
		return messages.changedDefinitionVisibility(afterDefinition.visibility ?? 'private');
	}
	if (beforeDefinition.rounds.length !== afterDefinition.rounds.length) {
		return beforeDefinition.rounds.length < afterDefinition.rounds.length
			? messages.addedRound
			: messages.removedRound;
	}
	for (let roundIndex = 0; roundIndex < afterDefinition.rounds.length; roundIndex += 1) {
		const beforeRound = beforeDefinition.rounds[roundIndex];
		const afterRound = afterDefinition.rounds[roundIndex];
		if (!beforeRound || !afterRound) {
			continue;
		}
		const roundLabel = afterRound.title || messages.fallbackRoundLabel(roundIndex + 1);
		if (beforeRound.title !== afterRound.title) {
			return messages.editedRoundTitle(beforeRound.title ?? '', afterRound.title ?? '');
		}
		if (beforeRound.id !== afterRound.id) {
			return messages.editedRoundId(beforeRound.id, afterRound.id);
		}
		if (beforeRound.steps.length !== afterRound.steps.length) {
			return beforeRound.steps.length < afterRound.steps.length
				? messages.addedStep(roundLabel)
				: messages.removedStep(roundLabel);
		}
		for (let stepIndex = 0; stepIndex < afterRound.steps.length; stepIndex += 1) {
			const beforeStep = beforeRound.steps[stepIndex];
			const afterStep = afterRound.steps[stepIndex];
			if (!beforeStep || !afterStep) {
				continue;
			}
			const label = stepLabel(afterStep, stepIndex, messages);
			if (beforeStep.id !== afterStep.id) {
				return messages.editedStepId(label);
			}
			if (beforeStep.title !== afterStep.title) {
				return messages.editedStepTitle(beforeStep.title, afterStep.title);
			}
			if (beforeStep.body !== afterStep.body) {
				return messages.editedStepBody(label);
			}
			if (JSON.stringify(beforeStep.media) !== JSON.stringify(afterStep.media)) {
				return messages.editedStepMedia(label);
			}
			if (JSON.stringify(beforeStep.player_input) !== JSON.stringify(afterStep.player_input)) {
				return messages.editedStepPlayerInput(label);
			}
			if (JSON.stringify(beforeStep.evaluation) !== JSON.stringify(afterStep.evaluation)) {
				return messages.editedStepScoring(label);
			}
			if (JSON.stringify(beforeStep.timer) !== JSON.stringify(afterStep.timer)) {
				return messages.editedStepTimer(label);
			}
			if (JSON.stringify(beforeStep.host_behavior) !== JSON.stringify(afterStep.host_behavior)) {
				return messages.editedStepHostBehavior(label);
			}
		}
	}
	return messages.editedDefinition;
}
