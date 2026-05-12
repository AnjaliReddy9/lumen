import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LumButtonComponent } from './lum-button.component';

describe('LumButtonComponent', () => {
  let fixture: ComponentFixture<LumButtonComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LumButtonComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(LumButtonComponent);
    fixture.componentRef.setInput('variant', 'primary');
    fixture.detectChanges();
  });

  it('creates', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('emits clicked on press', () => {
    const spy = jasmine.createSpy('clicked');
    fixture.componentInstance.clicked.subscribe(spy);
    const btn: HTMLButtonElement = fixture.nativeElement.querySelector('button');
    btn.click();
    expect(spy).toHaveBeenCalled();
  });
});
