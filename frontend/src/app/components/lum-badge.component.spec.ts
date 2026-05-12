import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LumBadgeComponent } from './lum-badge.component';

describe('LumBadgeComponent', () => {
  let fixture: ComponentFixture<LumBadgeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LumBadgeComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(LumBadgeComponent);
    fixture.componentRef.setInput('variant', 'success');
    fixture.detectChanges();
  });

  it('creates', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });
});
