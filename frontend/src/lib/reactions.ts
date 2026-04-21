export const CONTROLLER_REACTIONS = [
	{ id: 'laugh', emoji: '😂' },
	{ id: 'fire', emoji: '🔥' },
	{ id: 'clap', emoji: '👏' },
	{ id: 'shock', emoji: '😱' },
	{ id: 'poop', emoji: '💩' },
	{ id: 'vomit', emoji: '🤮' }
] as const;

export type ReactionOption = (typeof CONTROLLER_REACTIONS)[number];
export type ReactionId = ReactionOption['id'];
export type ReactionEmoji = ReactionOption['emoji'];

export const CONTROLLER_REACTION_EMOJIS = CONTROLLER_REACTIONS.map(
	(reaction) => reaction.emoji
) as readonly ReactionEmoji[];
