import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

export type ToastVariant = 'default' | 'success' | 'error';

export interface ToastMessage {
  id: number;
  message: string;
  variant: ToastVariant;
}

@Injectable({ providedIn: 'root' })
export class ToastService {
  private id = 0;
  readonly messages$ = new Subject<ToastMessage>();

  show(message: string, variant: ToastVariant = 'default'): void {
    this.messages$.next({ id: ++this.id, message, variant });
  }
}
