import {
  AfterViewInit,
  Component,
  ElementRef,
  Input,
  OnChanges,
  SimpleChanges,
  ViewChild,
  inject,
} from '@angular/core';
import { DOCUMENT } from '@angular/common';
import Prism from 'prismjs';
import 'prismjs/components/prism-sql';
import { LucideAngularModule, Copy, Check } from 'lucide-angular';

@Component({
  selector: 'lum-code-block',
  standalone: true,
  imports: [LucideAngularModule],
  template: `
    <div class="relative rounded-md border border-border bg-bg">
      <button
        type="button"
        (click)="copy()"
        class="absolute right-2 top-2 z-10 inline-flex rounded-md border border-border bg-bg-elevated p-2 text-text-secondary transition-colors duration-100 hover:bg-border/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        [attr.aria-label]="copied ? 'Copied' : 'Copy SQL'"
      >
        @if (copied) {
          <lucide-icon [img]="checkIcon" class="h-4 w-4 text-success" aria-hidden="true" />
        } @else {
          <lucide-icon [img]="copyIcon" class="h-4 w-4" aria-hidden="true" />
        }
      </button>
      <pre
        #pre
        class="max-h-[28rem] overflow-auto p-4 pr-14 font-mono text-xs leading-relaxed text-text"
      ><code class="language-sql"></code></pre>
    </div>
  `,
})
export class LumCodeBlockComponent implements AfterViewInit, OnChanges {
  private readonly doc = inject(DOCUMENT);

  @ViewChild('pre') preRef!: ElementRef<HTMLPreElement>;

  @Input({ required: true }) code!: string;
  @Input() language = 'sql';

  readonly copyIcon = Copy;
  readonly checkIcon = Check;

  copied = false;
  private copyTimer: ReturnType<typeof setTimeout> | null = null;

  ngAfterViewInit(): void {
    this.highlight();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!('code' in changes) || !this.preRef) {
      return;
    }
    this.highlight();
  }

  private highlight(): void {
    const el = this.preRef?.nativeElement.querySelector('code');
    if (!el) {
      return;
    }
    el.textContent = this.code;
    el.className = `language-${this.language}`;
    Prism.highlightElement(el);
  }

  copy(): void {
    const win = this.doc.defaultView;
    if (!win) {
      return;
    }
    void win.navigator.clipboard.writeText(this.code).then(() => {
      this.copied = true;
      if (this.copyTimer !== null) {
        win.clearTimeout(this.copyTimer);
      }
      this.copyTimer = win.setTimeout(() => {
        this.copied = false;
        this.copyTimer = null;
      }, 1600);
    });
  }
}
