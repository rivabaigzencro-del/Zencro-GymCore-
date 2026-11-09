"use client";

import { useSyncExternalStore } from "react";
import {
  type DueItem,
  INITIAL_DUES,
  subscribeDues,
  getStoredDues,
} from "./mock-data";

export function useDuesStore(): DueItem[] {
  return useSyncExternalStore(
    subscribeDues,
    getStoredDues,
    () => INITIAL_DUES
  );
}

