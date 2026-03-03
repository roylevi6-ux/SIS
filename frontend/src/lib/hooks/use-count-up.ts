'use client';

import { useEffect, useState } from 'react';

export function useCountUp(target: number, duration = 600): number {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const start = performance.now();
    let rafId: number;

    function update(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCurrent(Math.round(target * eased));
      if (progress < 1) rafId = requestAnimationFrame(update);
    }

    rafId = requestAnimationFrame(update);
    return () => cancelAnimationFrame(rafId);
  }, [target, duration]);

  return current;
}
