"use client";

import { useSyncExternalStore } from "react";
import {
  type MembershipPlanItem,
  INITIAL_PLANS,
  subscribePlans,
  getStoredPlans,
} from "./mock-data";

export function usePlansStore(): MembershipPlanItem[] {
  return useSyncExternalStore(
    subscribePlans,
    getStoredPlans,
    () => INITIAL_PLANS
  );
}

