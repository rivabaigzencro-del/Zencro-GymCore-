"use client";

import { useEffect, useState } from "react";

/**
 * Returns true once mounted on the client.
 * Guarantees that server render and initial client hydration render match identically.
 */
export function useMounted(): boolean {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    let active = true;
    requestAnimationFrame(() => {
      if (active) setMounted(true);
    });
    return () => {
      active = false;
    };
  }, []);

  return mounted;
}

