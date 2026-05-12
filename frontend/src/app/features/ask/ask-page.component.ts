import { Component, inject, OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';
import { FormsModule } from '@angular/forms';
import { NgxChartsModule } from '@swimlane/ngx-charts';
import { LumButtonComponent } from '../../components/lum-button.component';
import { LumTextareaComponent } from '../../components/lum-textarea.component';
import { LumCardComponent } from '../../components/lum-card.component';
import { LumBadgeComponent } from '../../components/lum-badge.component';
import { LumSkeletonComponent } from '../../components/lum-skeleton.component';
import { LumCodeBlockComponent } from '../../components/lum-code-block.component';
import { LumSpinnerComponent } from '../../components/lum-spinner.component';
import { LumenApiService } from '../../services/lumen-api.service';
import { ToastService } from '../../services/toast.service';
import type {
  AmbiguityIssue,
  Interpretation,
  QueryResponse,
  StreamEvent,
} from '../../models/api.types';
import { buildChartModel, type ChartModel } from './ask-chart.util';

type CardState = 'idle' | 'loading' | 'ready' | 'error';

@Component({
  selector: 'lum-ask-page',
  standalone: true,
  imports: [
    FormsModule,
    NgxChartsModule,
    LumButtonComponent,
    LumTextareaComponent,
    LumCardComponent,
    LumBadgeComponent,
    LumSkeletonComponent,
    LumCodeBlockComponent,
    LumSpinnerComponent,
  ],
  templateUrl: './ask-page.component.html',
})
export class AskPageComponent implements OnDestroy {
  private readonly api = inject(LumenApiService);
  private readonly toast = inject(ToastService);
  private streamSub: Subscription | null = null;

  question = '';
  skipInterpretation = false;
  skipValidation = false;
  optionsOpen = false;

  submitting = false;
  phaseLabel = '';

  interpState: CardState = 'idle';
  sqlState: CardState = 'idle';
  valState: CardState = 'idle';
  resState: CardState = 'idle';

  interpretation: Interpretation | null = null;
  result: QueryResponse | null = null;
  ambiguitySelections: Record<string, string> = {};
  resultsTab: 'table' | 'chart' = 'table';

  chartModel: ChartModel = { kind: 'none' };

  readonly chartColorScheme = 'cool';

  ngOnDestroy(): void {
    this.streamSub?.unsubscribe();
  }

  onKeydown(ev: KeyboardEvent): void {
    if ((ev.metaKey || ev.ctrlKey) && ev.key === 'Enter') {
      ev.preventDefault();
      this.submit();
    }
  }

  submit(): void {
    this.runStream({});
  }

  useAmbiguityAnswers(): void {
    this.runStream({ resolutions: { ...this.ambiguitySelections } });
  }

  private runStream(extra: { resolutions?: Record<string, string> }): void {
    const q = this.question.trim();
    if (!q || this.submitting) {
      return;
    }
    this.streamSub?.unsubscribe();
    this.submitting = true;
    this.resetCards();
    this.phaseLabel = 'Starting…';
    this.interpState = 'loading';
    this.sqlState = 'loading';
    this.valState = 'loading';
    this.resState = 'loading';

    this.streamSub = this.api
      .streamQuery({
        question: q,
        resolutions: extra.resolutions ?? null,
        skip_interpretation: this.skipInterpretation,
        skip_validation: this.skipValidation,
      })
      .subscribe({
        next: (ev: StreamEvent) => this.handleStream(ev),
        error: (err: unknown) => {
          this.submitting = false;
          this.toast.show(String(err), 'error');
          this.markError();
        },
        complete: () => {
          this.submitting = false;
          this.streamSub = null;
        },
      });
  }

  private resetCards(): void {
    this.interpretation = null;
    this.result = null;
    this.ambiguitySelections = {};
    this.chartModel = { kind: 'none' };
    this.interpState = 'idle';
    this.sqlState = 'idle';
    this.valState = 'idle';
    this.resState = 'idle';
  }

  private handleStream(ev: StreamEvent): void {
    if (ev.phase === 'interpreting') {
      this.phaseLabel = 'Interpreting…';
      if (!this.skipInterpretation) {
        this.interpState = 'loading';
      }
      return;
    }
    if (ev.phase === 'generated_sql') {
      this.phaseLabel = 'Generated SQL';
      if (ev.sql) {
        this.result = {
          interpretation: null,
          generated_sql: ev.sql,
          validation: { valid: true, issues: [], parsed_sql: null },
          rows: null,
          row_count: 0,
          error: null,
          latency_ms: 0,
          cost_usd: 0,
        };
        this.sqlState = 'ready';
      }
      return;
    }
    if (ev.phase === 'validating') {
      this.phaseLabel = 'Validating…';
      if (this.result) {
        this.result = {
          ...this.result,
          validation: {
            ...this.result.validation,
            valid: Boolean(ev.valid),
          },
        };
      }
      this.valState = 'ready';
      return;
    }
    if (ev.phase === 'executing') {
      this.phaseLabel = 'Executing…';
      if (this.result) {
        this.result = { ...this.result, row_count: ev.row_count ?? 0 };
      }
      return;
    }
    if (ev.phase === 'error') {
      this.phaseLabel = 'Error';
      this.toast.show(ev.detail ?? 'Stream error', 'error');
      this.markError();
      return;
    }
    if (ev.phase === 'done' && ev.payload) {
      this.phaseLabel = 'Done';
      this.applyPayload(ev.payload);
    }
  }

  private applyPayload(payload: QueryResponse): void {
    this.result = payload;
    this.interpretation = payload.interpretation;
    if (payload.interpretation?.ambiguities?.length) {
      for (const a of payload.interpretation.ambiguities) {
        const def = a.default ?? a.options[0] ?? '';
        this.ambiguitySelections[a.description] = def;
      }
    }
    this.interpState = payload.interpretation ? 'ready' : 'idle';
    if (this.skipInterpretation) {
      this.interpState = 'idle';
    }
    this.sqlState = payload.generated_sql ? 'ready' : 'error';
    this.valState = 'ready';
    if (payload.error === 'ambiguous_interpretation') {
      this.resState = 'idle';
    } else if (payload.error) {
      this.resState = 'error';
    } else {
      this.resState = 'ready';
    }
    if (payload.rows?.length) {
      this.chartModel = buildChartModel(payload.rows);
    }
  }

  private markError(): void {
    this.interpState = 'error';
    this.sqlState = 'error';
    this.valState = 'error';
    this.resState = 'error';
  }

  trackAmb(_i: number, a: AmbiguityIssue): string {
    return a.description;
  }

  objectKeys(row: Record<string, unknown>): string[] {
    return Object.keys(row);
  }

  formatCost(v: number): string {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(v);
  }

  formatLatency(ms: number): string {
    if (ms < 1000) {
      return `${ms} ms`;
    }
    return `${(ms / 1000).toFixed(1)} s`;
  }
}
