import { Component } from '@angular/core';
import { LucideAngularModule, Loader2 } from 'lucide-angular';

@Component({
  selector: 'lum-spinner',
  standalone: true,
  imports: [LucideAngularModule],
  template: `
    <lucide-icon [img]="icon" class="h-5 w-5 animate-spin text-accent" aria-hidden="true" />
  `,
})
export class LumSpinnerComponent {
  readonly icon = Loader2;
}
