export type FlatStepItem = {
	roundIndex: number;
	stepIndex: number;
	roundId: string;
	roundTitle: string;
	step: StepDefinition;
	stepKey: string;
	stepId: string;
	globalIndex: number;
};

export type StepHeaderAction = {
	label: string;
	shortcut?: string;
	icon: string;
	onClick: () => void;
	disabled?: boolean;
	variant?: 'default' | 'danger';
};
