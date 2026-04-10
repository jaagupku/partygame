import { derived } from 'svelte/store';

import { createLocalStorageStore } from '$lib/local-storage-store';

export const locales = [
	{ code: 'en', label: 'English' },
	{ code: 'et', label: 'Eesti' }
] as const;

export type Locale = (typeof locales)[number]['code'];

const fallbackLocale: Locale = 'en';

const translations = {
	en: {
		common: {
			manageDefinitions: 'Manage definitions',
			language: 'Language'
		},
		home: {
			title: 'Party Quiz Arena',
			subtitle: 'Pick how you want to enter the game.',
			create: 'Create',
			join: 'Join'
		}
	},
	et: {
		common: {
			manageDefinitions: 'Halda definitsioone',
			language: 'Keel'
		},
		home: {
			title: 'Peomangu Areen',
			subtitle: 'Vali, kuidas soovid mangu siseneda.',
			create: 'Loo',
			join: 'Liitu'
		}
	}
} as const satisfies Record<
	Locale,
	{ common: Record<string, string>; home: Record<string, string> }
>;

export const locale = createLocalStorageStore<Locale>('partygame-locale', fallbackLocale);

export const messages = derived(
	locale,
	($locale) => translations[$locale] ?? translations[fallbackLocale]
);
