import { Component, DestroyRef, inject, signal } from '@angular/core';
import { DecimalPipe, SlicePipe } from '@angular/common';
import { NgxChartsModule } from '@swimlane/ngx-charts';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { take } from 'rxjs';
import { LumenApiService } from '../../services/lumen-api.service';
import { ToastService } from '../../services/toast.service';
import type { EvalResult, EvalRun, EvalRunSummary } from '../../models/api.types';
import { LumCardComponent } from '../../components/lum-card.component';

@Component({
  selector: 'lum-benchmarks-page',
  standalone: true,
  imports: [NgxChartsModule, LumCardComponent, DecimalPipe, SlicePipe],
  templateUrl: './benchmarks-page.component.html',
})
export class BenchmarksPageComponent {
  private readonly api = inject(LumenApiService);
  private readonly toast = inject(ToastService);
  private readonly destroyRef = inject(DestroyRef);

  readonly runs = signal<EvalRunSummary[]>([]);
  readonly expanded = signal<string | null>(null);
  readonly detail = signal<EvalRun | null>(null);
  readonly loadingDetail = signal(false);

  diffChart: { name: string; value: number }[] = [];
  readonly chartColorScheme = 'cool';

  constructor() {
    this.api
      .listEvalRuns()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (r) => this.runs.set(r),
        error: () => this.toast.show('Could not load eval runs', 'error'),
      });
  }

  toggle(runId: string): void {
    if (this.expanded() === runId) {
      this.expanded.set(null);
      this.detail.set(null);
      return;
    }
    this.expanded.set(runId);
    this.loadingDetail.set(true);
    this.detail.set(null);
    this.api
      .getEvalRun(runId)
      .pipe(take(1))
      .subscribe({
        next: (run) => {
          if (this.expanded() !== runId) {
            return;
          }
          this.detail.set(run);
          this.diffChart = this.buildDiffChart(run);
          this.loadingDetail.set(false);
        },
        error: () => {
          if (this.expanded() !== runId) {
            return;
          }
          this.toast.show('Run not found', 'error');
          this.loadingDetail.set(false);
        },
      });
  }

  private buildDiffChart(run: EvalRun): { name: string; value: number }[] {
    const by = run.summary.by_difficulty;
    if (!by) {
      return [];
    }
    return Object.entries(by).map(([name, s]) => ({
      name,
      value: s.execution_accuracy,
    }));
  }

  trackResult(_i: number, r: EvalResult): string {
    return r.case_id;
  }
}
