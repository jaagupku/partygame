import { getMessages } from '$lib/i18n';

export function drawingText(
	value: DrawingText | null | undefined,
	kind: 'topic' | 'criterion',
	language: 'en' | 'et'
): string {
	if (!value) return '';
	if (value.fallback === null) return value.text;
	const copy = getMessages(language).drawingMashup;
	return (kind === 'topic' ? copy.fallbackTopics : copy.fallbackCriteria)[value.fallback] ?? '';
}
