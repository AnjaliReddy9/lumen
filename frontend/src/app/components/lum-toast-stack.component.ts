import { Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ToastService, type ToastMessage } from '../services/toast.service';

@Component({
  selector: 'lum-toast-stack',
  standalone: true,
  template: `
    <div
      class="pointer-events-none fixed bottom-4 right-4 z-50 flex max-w-sm flex-col gap-2"
      aria-live="polite"
    >
      @for (t of messages(); track t.id) {
        @switch (t.variant) {
          @case ('success') {
            <div
              class="pointer-events-auto rounded-md border border-success bg-bg-elevated px-4 py-3 text-sm text-success transition-opacity duration-150"
            >
              {{ t.message }}
            </div>
          }
          @case ('error') {
            <div
              class="pointer-events-auto rounded-md border border-error bg-bg-elevated px-4 py-3 text-sm text-error transition-opacity duration-150"
            >
              {{ t.message }}
            </div>
          }
          @default {
            <div
              class="pointer-events-auto rounded-md border border-border bg-bg-elevated px-4 py-3 text-sm text-text transition-opacity duration-150"
            >
              {{ t.message }}
            </div>
          }
        }
      }
    </div>
  `,
})
export class LumToastStackComponent {
  private readonly toast = inject(ToastService);
  readonly messages = signal<ToastMessage[]>([]);

  constructor() {
    this.toast.messages$.pipe(takeUntilDestroyed()).subscribe((m) => {
      this.messages.update((list) => [...list, m]);
      setTimeout(() => {
        this.messages.update((list) => list.filter((x) => x.id !== m.id));
      }, 4000);
    });
  }
}
