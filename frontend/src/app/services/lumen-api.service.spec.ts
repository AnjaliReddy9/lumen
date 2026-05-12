import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { LumenApiService } from './lumen-api.service';

describe('LumenApiService', () => {
  let service: LumenApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), LumenApiService],
    });
    service = TestBed.inject(LumenApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('getHealth GETs a URL ending with /health', () => {
    service.getHealth().subscribe((r) => {
      expect(r.status).toBe('ok');
    });
    const req = http.expectOne((r) => r.method === 'GET' && r.url.endsWith('/health'));
    req.flush({ status: 'ok', version: '0.1.0' });
  });

  it('getReady GETs /ready', () => {
    service.getReady().subscribe((b) => {
      expect(b).toEqual({ ok: true });
    });
    http.expectOne((r) => r.method === 'GET' && r.url.endsWith('/ready')).flush({ ok: true });
  });

  it('getSchema GETs /schema', () => {
    service.getSchema().subscribe((s) => {
      expect(s.tables).toEqual([]);
    });
    http.expectOne((r) => r.method === 'GET' && r.url.endsWith('/schema')).flush({ tables: [] });
  });

  it('getSemanticModel GETs /semantic', () => {
    service.getSemanticModel().subscribe((m) => {
      expect(m.entities).toEqual([]);
    });
    http
      .expectOne((r) => r.method === 'GET' && r.url.endsWith('/semantic'))
      .flush({
        entities: [],
        metrics: [],
        relationships: [],
      });
  });

  it('interpret POSTs /interpret', () => {
    service.interpret('q').subscribe();
    const req = http.expectOne((r) => r.method === 'POST' && r.url.endsWith('/interpret'));
    expect(req.request.body).toEqual({ question: 'q' });
    req.flush({ intent: {}, ambiguities: [] });
  });

  it('query POSTs /query', () => {
    const body = {
      question: 'x',
      resolutions: null,
      skip_interpretation: false,
      skip_validation: false,
    };
    service.query(body).subscribe();
    const req = http.expectOne((r) => r.method === 'POST' && r.url.endsWith('/query'));
    expect(req.request.body).toEqual(body);
    req.flush({
      interpretation: null,
      generated_sql: 'SELECT 1',
      validation: { valid: true, issues: [], parsed_sql: null },
      rows: [],
      row_count: 0,
      error: null,
      latency_ms: 0,
      cost_usd: 0,
    });
  });

  it('listEvalRuns GETs /eval/runs', () => {
    service.listEvalRuns().subscribe((rows) => {
      expect(rows.length).toBe(0);
    });
    http.expectOne((r) => r.method === 'GET' && r.url.endsWith('/eval/runs')).flush([]);
  });

  it('getEvalRun GETs encoded path', () => {
    service.getEvalRun('run/1').subscribe((run) => {
      expect(run.run_id).toBe('run%2F1');
    });
    http
      .expectOne((r) => r.method === 'GET' && r.url.includes('/eval/runs/'))
      .flush({
        run_id: 'run%2F1',
        benchmark: 'chinook',
        model: 'm',
        config: {},
        started_at: '2020-01-01T00:00:00',
        completed_at: null,
        cases_total: 0,
        cases_completed: 0,
        results: [],
        summary: {
          execution_accuracy: 0,
          validation_pass_rate: 0,
          generation_success_rate: 0,
          avg_latency_ms: 0,
          total_cost_usd: 0,
          by_difficulty: null,
        },
      });
  });
});
