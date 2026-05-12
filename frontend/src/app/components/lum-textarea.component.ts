import { Component, Input, output } from '@angular/core';

@Component({
  selector: 'lum-textarea',
  standalone: true,
  template: `
    <label class="block">
      @if (label) {
        <span class="mb-1.5 block text-sm font-medium text-text-secondary">{{ label }}</span>
      }
      <textarea
        [rows]="rows"
        [value]="value"
        (input)="onInput($event)"
        (keydown)="textareaKeydown.emit($event)"
        [placeholder]="placeholder"
        [attr.aria-invalid]="error ? 'true' : 'false'"
        class="w-full resize-y rounded-md border bg-bg px-3 py-2 text-sm text-text transition-colors duration-100 placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        [class.border-error]="error"
        [class.border-border]="!error"
      ></textarea>
      @if (error) {
        <span class="mt-1 block text-xs text-error" role="alert">{{ error }}</span>
      }
    </label>
  `,
})
export class LumTextareaComponent {
  @Input({ required: true }) label!: string;
  @Input() value = '';
  @Input() placeholder = '';
  @Input() rows = 4;
  @Input() error = '';
  readonly valueChange = output<string>();
  readonly textareaKeydown = output<KeyboardEvent>();

  onInput(ev: Event): void {
    const t = ev.target as HTMLTextAreaElement | null;
    this.valueChange.emit(t?.value ?? '');
  }
}
