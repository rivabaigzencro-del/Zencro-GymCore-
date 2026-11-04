"use client";

import { useSyncExternalStore } from "react";
import {
  type PaymentRecord,
  INITIAL_PAYMENTS,
  subscribePayments,
  getStoredPayments,
} from "./mock-data";

export function usePaymentsStore(): PaymentRecord[] {
  return useSyncExternalStore(
    subscribePayments,
    getStoredPayments,
    () => INITIAL_PAYMENTS
  );
}

