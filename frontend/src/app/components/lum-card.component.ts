import { Component, Input } from '@angular/core';

@Component({
  selector: 'lum-card',
  standalone: true,
  template: `
    <section
      class="rounded-lg border border-border bg-bg-elevated transition-opacity duration-150 ease-out"
    >
      @if (title) {
        <header class="border-b border-border px-4 py-3 text-sm font-medium text-text">
          {{ title }}
        </header>
      }
      <div class="px-4 py-4">
        <ng-content />
      </div>
    </section>
  `,
})
export class LumCardComponent {
  @Input() title = '';
}
