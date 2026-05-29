export async function readErrorDetail(response: Response): Promise<string> {
	try {
		const payload = await response.json();
		if (typeof payload?.detail === 'string') {
			return payload.detail;
		}
	} catch {
		return '';
	}
	return '';
}
