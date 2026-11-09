"use client";

import { useSyncExternalStore } from "react";
import {
  type GymSettings,
  INITIAL_SETTINGS,
  subscribeSettings,
  getStoredSettings,
} from "./mock-data";

export function useSettingsStore(): GymSettings {
  return useSyncExternalStore(
    subscribeSettings,
    getStoredSettings,
    () => INITIAL_SETTINGS
  );
}

