'use client';

import { useEffect, useRef, useState } from 'react';

export function useCountUp(target: number, duration = 600): number {
  const [current, setCurrent] = useState(0);
  const prevTarget = useRef(0);

  useEffect(() => {
    if (target === prevTarget.current) return;
    prevTarget.current = target;

    const start = performance.now();
    const from = 0;

    let rafId: number;

    function update(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCurrent(Math.round(from + (target - from) * eased));
      if (progress < 1) rafId = requestAnimationFrame(update);
    }

    rafId = requestAnimationFrame(update);
    return () => cancelAnimationFrame(rafId);
  }, [target, duration]);

  return current;
}
