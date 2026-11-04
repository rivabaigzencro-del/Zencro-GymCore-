"use client";

import { useSyncExternalStore } from "react";
import {
  type AttendanceRecord,
  INITIAL_ATTENDANCE,
  subscribeAttendance,
  getStoredAttendance,
} from "./mock-data";

export function useAttendanceStore(): AttendanceRecord[] {
  return useSyncExternalStore(
    subscribeAttendance,
    getStoredAttendance,
    () => INITIAL_ATTENDANCE
  );
}

