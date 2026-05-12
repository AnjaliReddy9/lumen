import { Component, DestroyRef, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { LumenApiService } from '../../services/lumen-api.service';
import { ToastService } from '../../services/toast.service';
import type { Entity, Schema, SemanticModel, Table } from '../../models/api.types';
import { LumInputComponent } from '../../components/lum-input.component';
import { LumCardComponent } from '../../components/lum-card.component';

@Component({
  selector: 'lum-schema-page',
  standalone: true,
  imports: [FormsModule, LumInputComponent, LumCardComponent],
  templateUrl: './schema-page.component.html',
})
export class SchemaPageComponent {
  private readonly api = inject(LumenApiService);
  private readonly toast = inject(ToastService);

  readonly semantic = signal<SemanticModel | null>(null);
  readonly schema = signal<Schema | null>(null);
  readonly selectedEntity = signal<Entity | null>(null);
  tableSearch = '';
  readonly loading = signal(true);

  constructor() {
    const dr = inject(DestroyRef);
    forkJoin({
      semantic: this.api.getSemanticModel(),
      schema: this.api.getSchema(),
    })
      .pipe(takeUntilDestroyed(dr))
      .subscribe({
        next: ({ semantic, schema }) => {
          this.semantic.set(semantic);
          this.schema.set(schema);
          const first = semantic.entities[0] ?? null;
          this.selectedEntity.set(first);
          this.loading.set(false);
        },
        error: () => {
          this.toast.show('Failed to load schema', 'error');
          this.loading.set(false);
        },
      });
  }

  selectEntity(e: Entity): void {
    this.selectedEntity.set(e);
  }

  metricsForEntity(name: string): string[] {
    const m = this.semantic();
    if (!m) {
      return [];
    }
    return m.metrics.filter((x) => x.entity === name).map((x) => x.name);
  }

  relationshipsForEntity(name: string): string[] {
    const m = this.semantic();
    if (!m) {
      return [];
    }
    return m.relationships
      .filter((r) => r.from === name || r.to === name)
      .map((r) => `${r.from}.${r.from_key} → ${r.to}.${r.to_key} (${r.type})`);
  }

  filteredTables(): Table[] {
    const s = this.schema();
    if (!s) {
      return [];
    }
    const q = this.tableSearch.trim().toLowerCase();
    if (!q) {
      return s.tables;
    }
    return s.tables.filter((t) => t.name.toLowerCase().includes(q));
  }
}
