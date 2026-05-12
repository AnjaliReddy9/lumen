import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { LumToastStackComponent } from './components/lum-toast-stack.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, LumToastStackComponent],
  template: `<lum-toast-stack /><router-outlet />`,
})
export class AppComponent {}
