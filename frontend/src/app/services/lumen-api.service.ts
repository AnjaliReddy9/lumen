import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subscriber } from 'rxjs';
import { environment } from '../../environments/environment';
import type {
  EvalRun,
  EvalRunSummary,
  Interpretation,
  QueryRequest,
  QueryResponse,
  Schema,
  SemanticModel,
  StreamEvent,
} from '../models/api.types';

@Injectable({ providedIn: 'root' })
export class LumenApiService {
  private readonly http = inject(HttpClient);

  private url(path: string): string {
    const p = path.startsWith('/') ? path : `/${path}`;
    if (environment.production) {
      return `${environment.apiPrefix}${p}`;
    }
    return `${environment.apiBase}${p}`;
  }

  getHealth(): Observable<{ status: string; version: string }> {
    return this.http.get<{ status: string; version: string }>(this.url('/health'));
  }

  getReady(): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(this.url('/ready'));
  }

  getSchema(): Observable<Schema> {
    return this.http.get<Schema>(this.url('/schema'));
  }

  getSemanticModel(): Observable<SemanticModel> {
    return this.http.get<SemanticModel>(this.url('/semantic'));
  }

  interpret(question: string): Observable<Interpretation> {
    return this.http.post<Interpretation>(this.url('/interpret'), { question });
  }

  query(req: QueryRequest): Observable<QueryResponse> {
    return this.http.post<QueryResponse>(this.url('/query'), req);
  }

  streamQuery(req: QueryRequest): Observable<StreamEvent> {
    return new Observable((observer: Subscriber<StreamEvent>) => {
      const controller = new AbortController();
      void (async () => {
        try {
          const response = await fetch(this.url('/query/stream'), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Accept: 'text/event-stream',
            },
            body: JSON.stringify(req),
            signal: controller.signal,
          });
          if (!response.ok) {
            observer.error(new Error(`HTTP ${response.status}`));
            return;
          }
          const reader = response.body?.getReader();
          if (!reader) {
            observer.error(new Error('No response body'));
            return;
          }
          const decoder = new TextDecoder();
          let carry = '';
          while (true) {
            const { done, value } = await reader.read();
            if (done) {
              break;
            }
            carry += decoder.decode(value, { stream: true });
            const parts = carry.split('\n\n');
            carry = parts.pop() ?? '';
            for (const block of parts) {
              for (const line of block.split('\n')) {
                if (line.startsWith('data: ')) {
                  const raw = line.slice(6).trim();
                  if (raw) {
                    const data = JSON.parse(raw) as StreamEvent;
                    observer.next(data);
                  }
                }
              }
            }
          }
          observer.complete();
        } catch (e: unknown) {
          if ((e as { name?: string }).name === 'AbortError') {
            observer.complete();
          } else {
            observer.error(e);
          }
        }
      })();
      return () => controller.abort();
    });
  }

  listEvalRuns(): Observable<EvalRunSummary[]> {
    return this.http.get<EvalRunSummary[]>(this.url('/eval/runs'));
  }

  getEvalRun(runId: string): Observable<EvalRun> {
    return this.http.get<EvalRun>(this.url(`/eval/runs/${encodeURIComponent(runId)}`));
  }
}
