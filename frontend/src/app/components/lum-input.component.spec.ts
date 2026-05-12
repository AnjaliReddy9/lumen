import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LumInputComponent } from './lum-input.component';

describe('LumInputComponent', () => {
  let fixture: ComponentFixture<LumInputComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LumInputComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(LumInputComponent);
    fixture.componentRef.setInput('label', 'Name');
    fixture.detectChanges();
  });

  it('creates', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });
});
