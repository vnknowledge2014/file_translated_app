import { writable } from 'svelte/store';
import { setLanguageTag, sourceLanguageTag, type AvailableLanguageTag, availableLanguageTags } from '../paraglide/runtime.js';

function createI18nStore() {
    // Check localStorage or browser preference, default to sourceLanguageTag
    const getInitialLang = (): AvailableLanguageTag => {
        if (typeof window === 'undefined') return sourceLanguageTag;
        const stored = localStorage.getItem('ui_lang') as AvailableLanguageTag;
        if (stored && availableLanguageTags.includes(stored)) return stored;
        
        const navLangs = navigator.languages || [navigator.language];
        for (const lang of navLangs) {
            const shortCode = lang.split('-')[0] as AvailableLanguageTag;
            if (availableLanguageTags.includes(shortCode)) return shortCode;
        }
        return sourceLanguageTag;
    };

    const currentLang = getInitialLang();
    setLanguageTag(currentLang);
    
    const { subscribe, set } = writable<AvailableLanguageTag>(currentLang);

    return {
        subscribe,
        setLanguage: (lang: AvailableLanguageTag) => {
            if (availableLanguageTags.includes(lang)) {
                setLanguageTag(lang);
                set(lang);
                if (typeof window !== 'undefined') {
                    localStorage.setItem('ui_lang', lang);
                }
            }
        }
    };
}

export const uiLang = createI18nStore();
