import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LumCardComponent } from './lum-card.component';

describe('LumCardComponent', () => {
  let fixture: ComponentFixture<LumCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LumCardComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(LumCardComponent);
    fixture.componentRef.setInput('title', 'T');
    fixture.detectChanges();
  });

  it('creates', () => {
    expect(fixture.nativeElement.textContent).toContain('T');
  });
});
