"use client";

import { useSyncExternalStore } from "react";
import {
  type UserSession,
  getActiveSession,
  subscribeSession,
} from "./api-client";

export function useSessionStore(): UserSession | null {
  return useSyncExternalStore(
    subscribeSession,
    getActiveSession,
    () => null
  );
}
