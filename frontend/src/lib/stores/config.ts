import { writable } from 'svelte/store';
import { fetchLanguages, fetchDomains } from '$lib/api';

export type Language = {
    code: string;
    name: string;
    native_name: string;
    flag: string;
};

export type Domain = {
    code: string;
    name: string;
    icon: string;
};

export const languages = writable<Language[]>([]);
export const domains = writable<Domain[]>([]);

export const sourceLang = writable<string>('auto');
export const targetLang = writable<string>('vi');
export const currentDomain = writable<string>('general');

export async function loadConfig() {
    try {
        const langData = await fetchLanguages();
        languages.set(langData.languages);
        if (langData.current) {
            if (langData.current.source) sourceLang.set(langData.current.source);
            if (langData.current.target) targetLang.set(langData.current.target);
        }

        const domData = await fetchDomains();
        domains.set(domData.domains);
        
        // Restore from localStorage if present
        const storedSrc = localStorage.getItem('tr_sourceLang');
        const storedTgt = localStorage.getItem('tr_targetLang');
        const storedDom = localStorage.getItem('tr_domain');
        
        if (storedSrc) sourceLang.set(storedSrc);
        if (storedTgt) targetLang.set(storedTgt);
        if (storedDom) currentDomain.set(storedDom);
        
    } catch (e) {
        console.error('Failed to load config:', e);
    }
}
