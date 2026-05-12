import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./layout/app-shell.component').then((m) => m.AppShellComponent),
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'ask' },
      {
        path: 'ask',
        loadComponent: () =>
          import('./features/ask/ask-page.component').then((m) => m.AskPageComponent),
      },
      {
        path: 'schema',
        loadComponent: () =>
          import('./features/schema/schema-page.component').then((m) => m.SchemaPageComponent),
      },
      {
        path: 'benchmarks',
        loadComponent: () =>
          import('./features/benchmarks/benchmarks-page.component').then(
            (m) => m.BenchmarksPageComponent,
          ),
      },
    ],
  },
];
