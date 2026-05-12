import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormsModule } from '@angular/forms';
import { Observable, Subject } from 'rxjs';
import { AskPageComponent } from './ask-page.component';
import { LumenApiService } from '../../services/lumen-api.service';
import { ToastService } from '../../services/toast.service';
import type { QueryResponse, StreamEvent } from '../../models/api.types';

describe('AskPageComponent', () => {
  let fixture: ComponentFixture<AskPageComponent>;
  let stream$: Subject<StreamEvent>;

  beforeEach(async () => {
    stream$ = new Subject<StreamEvent>();
    await TestBed.configureTestingModule({
      imports: [AskPageComponent, FormsModule],
      providers: [
        {
          provide: LumenApiService,
          useValue: {
            streamQuery(): Observable<StreamEvent> {
              return stream$.asObservable();
            },
          },
        },
        { provide: ToastService, useValue: { show: jasmine.createSpy('show') } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(AskPageComponent);
    fixture.detectChanges();
  });

  it('creates', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows interpretation after stream done payload', () => {
    const comp = fixture.componentInstance;
    comp.question = 'test';
    comp.submit();
    stream$.next({ phase: 'interpreting' });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Interpreting');

    const payload: QueryResponse = {
      interpretation: {
        confidence: 'high',
        ambiguities: [],
        intent: {
          question: 'test',
          intent_summary: 'You want revenue.',
          entities_referenced: ['orders'],
          metrics_referenced: [],
          dimensions_referenced: [],
          time_grain: null,
          filters: [],
          sort: null,
          limit: null,
        },
      },
      generated_sql: 'SELECT 1',
      validation: { valid: true, issues: [], parsed_sql: null },
      rows: [{ a: 1 }],
      row_count: 1,
      error: null,
      latency_ms: 100,
      cost_usd: 0.01,
    };
    stream$.next({ phase: 'done', payload });
    stream$.complete();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('You want revenue.');
    expect(fixture.nativeElement.textContent).toContain('Generated SQL');
  });
});
