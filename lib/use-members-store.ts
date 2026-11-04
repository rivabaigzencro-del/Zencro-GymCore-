"use client";

import { useSyncExternalStore } from "react";
import {
  type Member,
  INITIAL_MEMBERS,
  subscribeMembers,
  getStoredMembers,
} from "./mock-data";

export function useMembersStore(): Member[] {
  return useSyncExternalStore(
    subscribeMembers,
    getStoredMembers,
    () => INITIAL_MEMBERS
  );
}

