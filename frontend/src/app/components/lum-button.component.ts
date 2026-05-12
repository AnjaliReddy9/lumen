import { Component, Input, output } from '@angular/core';
import { NgClass } from '@angular/common';
import { LucideAngularModule, Loader2 } from 'lucide-angular';

export type LumButtonVariant = 'primary' | 'secondary' | 'ghost';
export type LumButtonSize = 'sm' | 'md' | 'lg';

@Component({
  selector: 'lum-button',
  standalone: true,
  imports: [NgClass, LucideAngularModule],
  template: `
    <button
      [type]="type"
      [disabled]="disabled || loading"
      [attr.aria-busy]="loading"
      (click)="clicked.emit($event)"
      [ngClass]="classes()"
      class="inline-flex items-center justify-center gap-2 rounded-md border font-medium transition-colors duration-100 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:pointer-events-none disabled:opacity-50"
    >
      @if (loading) {
        <lucide-icon [img]="loaderIcon" class="h-4 w-4 animate-spin" aria-hidden="true" />
      }
      <ng-content />
    </button>
  `,
})
export class LumButtonComponent {
  readonly loaderIcon = Loader2;
  readonly clicked = output<MouseEvent>();

  @Input({ required: true }) variant!: LumButtonVariant;
  @Input() size: LumButtonSize = 'md';
  @Input() type: 'button' | 'submit' = 'button';
  @Input() disabled = false;
  @Input() loading = false;

  classes(): Record<string, boolean> {
    const base = {
      'px-3 py-1.5 text-sm': this.size === 'sm',
      'px-4 py-2 text-sm': this.size === 'md',
      'px-5 py-2.5 text-base': this.size === 'lg',
    };
    if (this.variant === 'primary') {
      return {
        ...base,
        'border-transparent bg-accent text-white hover:bg-accent-hover': true,
      };
    }
    if (this.variant === 'secondary') {
      return {
        ...base,
        'border-border bg-bg-elevated text-text hover:bg-border/40': true,
      };
    }
    return {
      ...base,
      'border-transparent bg-transparent text-text hover:bg-bg-elevated': true,
    };
  }
}
