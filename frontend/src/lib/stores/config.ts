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
export const targetLang = writable<string>('en');
export const currentDomain = writable<string>('general');

export async function loadConfig() {
    try {
        const langData = await fetchLanguages();
        // API returns a flat array of language objects
        const langList = Array.isArray(langData) ? langData : (langData.languages || []);
        languages.set(langList);

        const domData = await fetchDomains();
        const domList = Array.isArray(domData) ? domData : (domData.domains || []);
        domains.set(domList);
        
        // Restore from localStorage if present (user's previous selections)
        const storedSrc = localStorage.getItem('tr_sourceLang');
        const storedTgt = localStorage.getItem('tr_targetLang');
        const storedDom = localStorage.getItem('tr_domain');
        
        if (storedSrc) sourceLang.set(storedSrc);
        if (storedTgt) targetLang.set(storedTgt);
        if (storedDom) currentDomain.set(storedDom);
        
        // Persist changes to localStorage
        sourceLang.subscribe(v => localStorage.setItem('tr_sourceLang', v));
        targetLang.subscribe(v => localStorage.setItem('tr_targetLang', v));
        currentDomain.subscribe(v => localStorage.setItem('tr_domain', v));
        
    } catch (e) {
        console.error('Failed to load config:', e);
    }
}
