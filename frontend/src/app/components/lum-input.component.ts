import { Component, Input, output } from '@angular/core';

@Component({
  selector: 'lum-input',
  standalone: true,
  template: `
    <label class="block">
      @if (label) {
        <span class="mb-1.5 block text-sm font-medium text-text-secondary">{{ label }}</span>
      }
      <input
        [type]="type"
        [value]="value"
        (input)="onInput($event)"
        [placeholder]="placeholder"
        [attr.aria-invalid]="error ? 'true' : 'false'"
        [attr.aria-describedby]="descId || null"
        class="w-full rounded-md border bg-bg px-3 py-2 text-sm text-text transition-colors duration-100 placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        [class.border-error]="error"
        [class.border-border]="!error"
      />
      @if (helper && !error) {
        <span [id]="descId" class="mt-1 block text-xs text-text-muted">{{ helper }}</span>
      }
      @if (error) {
        <span [id]="descId" class="mt-1 block text-xs text-error" role="alert">{{ error }}</span>
      }
    </label>
  `,
})
export class LumInputComponent {
  @Input({ required: true }) label!: string;
  @Input() value = '';
  @Input() placeholder = '';
  @Input() type: 'text' | 'search' = 'text';
  @Input() helper = '';
  @Input() error = '';
  @Input() descId = '';
  readonly valueChange = output<string>();

  onInput(ev: Event): void {
    const t = ev.target as HTMLInputElement | null;
    this.valueChange.emit(t?.value ?? '');
  }
}
