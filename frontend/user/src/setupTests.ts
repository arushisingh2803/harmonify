import '@testing-library/jest-dom';

global.IntersectionObserver = class IntersectionObserver {
  constructor(callback: any) {}
  observe() {}
  unobserve() {}
  disconnect() {}
} as any;

HTMLCanvasElement.prototype.getContext = () => null as any;

global.requestAnimationFrame = (cb) => setTimeout(cb, 0) as any;
global.cancelAnimationFrame  = (id) => clearTimeout(id);