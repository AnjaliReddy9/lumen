import { Injectable, signal, effect } from '@angular/core';

const STORAGE_KEY = 'lumen-theme-dark';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  readonly dark = signal(this.readInitial());

  constructor() {
    effect(() => {
      const isDark = this.dark();
      document.documentElement.classList.toggle('dark', isDark);
      localStorage.setItem(STORAGE_KEY, isDark ? '1' : '0');
    });
  }

  toggle(): void {
    this.dark.update((v) => !v);
  }

  private readInitial(): boolean {
    if (typeof localStorage === 'undefined') {
      return true;
    }
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === '0') {
      return false;
    }
    if (stored === '1') {
      return true;
    }
    return true;
  }
}
