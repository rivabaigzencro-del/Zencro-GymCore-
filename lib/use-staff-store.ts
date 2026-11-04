"use client";

import { useSyncExternalStore } from "react";
import {
  type StaffMember,
  INITIAL_STAFF,
  subscribeStaff,
  getStoredStaff,
} from "./mock-data";

export function useStaffStore(): StaffMember[] {
  return useSyncExternalStore(
    subscribeStaff,
    getStoredStaff,
    () => INITIAL_STAFF
  );
}

