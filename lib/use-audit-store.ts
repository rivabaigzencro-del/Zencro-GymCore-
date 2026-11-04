"use client";

import { useSyncExternalStore } from "react";
import {
  type AuditRecord,
  getStoredAuditLogs,
  subscribeAuditLogs,
  INITIAL_AUDIT_LOGS,
} from "./audit-trail";

export function useAuditStore(): AuditRecord[] {
  return useSyncExternalStore(
    subscribeAuditLogs,
    getStoredAuditLogs,
    () => INITIAL_AUDIT_LOGS
  );
}

