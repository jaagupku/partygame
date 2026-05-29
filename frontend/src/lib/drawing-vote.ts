export function getDrawingVoteRubric(step?: RuntimeStepState): string {
	const answer = step?.evaluation_answer;
	if (answer === undefined || answer === null) {
		return '';
	}
	return String(answer).trim();
}
