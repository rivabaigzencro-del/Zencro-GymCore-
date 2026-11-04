"use client";

import { useSyncExternalStore } from "react";

const emptySubscribe = () => () => {};

/**
 * Returns true once mounted on the client.
 * Uses useSyncExternalStore to prevent cascading renders and hydration mismatches
 * while fully conforming to React 19 / ESLint rules.
 */
export function useMounted(): boolean {
  return useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false
  );
}

