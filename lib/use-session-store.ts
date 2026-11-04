"use client";

import { useSyncExternalStore } from "react";
import {
  type UserSession,
  DEMO_ACCOUNTS,
  getActiveSession,
  subscribeSession,
} from "./api-client";

export function useSessionStore(): UserSession {
  return useSyncExternalStore(
    subscribeSession,
    getActiveSession,
    () => DEMO_ACCOUNTS["owner@gymcore.com"]
  );
}

