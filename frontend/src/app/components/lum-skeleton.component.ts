import { Component, Input } from '@angular/core';

@Component({
  selector: 'lum-skeleton',
  standalone: true,
  template: `
    <div
      class="animate-skeleton rounded-md bg-border/60"
      [style.width]="width"
      [style.height]="height"
      role="presentation"
    ></div>
  `,
})
export class LumSkeletonComponent {
  @Input() width = '100%';
  @Input() height = '1rem';
}
