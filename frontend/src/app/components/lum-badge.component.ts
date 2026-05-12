import { Component, Input } from '@angular/core';
import { NgClass } from '@angular/common';

export type LumBadgeVariant = 'default' | 'success' | 'warning' | 'error';

@Component({
  selector: 'lum-badge',
  standalone: true,
  imports: [NgClass],
  template: `
    <span
      [ngClass]="pillClass()"
      class="inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium"
    >
      <ng-content />
    </span>
  `,
})
export class LumBadgeComponent {
  @Input() variant: LumBadgeVariant = 'default';

  pillClass(): string {
    switch (this.variant) {
      case 'success':
        return 'border-success/30 bg-success/10 text-success';
      case 'warning':
        return 'border-warning/30 bg-warning/10 text-warning';
      case 'error':
        return 'border-error/30 bg-error/10 text-error';
      default:
        return 'border-border bg-bg text-text-secondary';
    }
  }
}
