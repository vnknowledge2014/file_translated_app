import { writable } from 'svelte/store';

export type ToastType = 'success' | 'error' | 'info';

export interface ToastMessage {
    id: number;
    message: string;
    type: ToastType;
}

const { subscribe, update } = writable<ToastMessage[]>([]);
let idCounter = 0;

export const toastStore = {
    subscribe,
    add: (message: string, type: ToastType = 'info', duration = 4000) => {
        const id = ++idCounter;
        update(toasts => [...toasts, { id, message, type }]);
        setTimeout(() => {
            update(toasts => toasts.filter(t => t.id !== id));
        }, duration);
    },
    remove: (id: number) => {
        update(toasts => toasts.filter(t => t.id !== id));
    }
};

export function showToast(message: string, type: ToastType = 'info') {
    toastStore.add(message, type);
}
