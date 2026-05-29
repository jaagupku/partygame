export function canEditDefinitionForUser(
	definition: { can_edit?: boolean; owner_user_id?: string | null },
	user: User | null
): boolean {
	if (definition.can_edit) {
		return true;
	}
	if (!user) {
		return false;
	}
	return user.role === 'admin' || definition.owner_user_id === user.id;
}
