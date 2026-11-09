/**
 * Central ID generation and numeric sorting utility for GYMCORE.
 *
 * Ensures:
 * 1. IDs are determined using the highest existing numeric suffix (not array length or index).
 * 2. Deleted IDs are never reused (tracked via persistent high-water mark counters).
 * 3. Sorting is strictly numeric ascending (e.g. GYM001 < GYM002 < GYM009 < GYM010),
 *    preventing lexicographical ordering bugs.
 * 4. IDs remain completely stable during edits, sorting, filtering, and deletion.
 */

export const MEMBER_ID_COUNTER_KEY = "gymcore_member_id_counter";
export const STAFF_ID_COUNTER_KEY = "gymcore_staff_id_counter";

/**
 * Extracts the integer numeric suffix from an ID string.
 * Examples: "GYM001" -> 1, "GYM007" -> 7, "STF012" -> 12, "ATT-1005" -> 1005.
 * Returns 0 if no digits found.
 */
export function extractNumericSuffix(id?: string | null): number {
  if (!id) return 0;
  const match = String(id).match(/\d+/);
  return match ? parseInt(match[0], 10) : 0;
}

/**
 * Comparator for ascending numeric ID sorting.
 */
export function compareNumericIds<T extends { id: string }>(a: T, b: T): number {
  const numA = extractNumericSuffix(a.id);
  const numB = extractNumericSuffix(b.id);
  if (numA !== numB) {
    return numA - numB;
  }
  return a.id.localeCompare(b.id);
}

/**
 * Returns a new array of members sorted in numeric ascending ID order.
 */
export function sortMembersByNumericId<T extends { id: string }>(items: T[]): T[] {
  return [...items].sort(compareNumericIds);
}

/**
 * Returns a new array of staff sorted in numeric ascending ID order.
 */
export function sortStaffByNumericId<T extends { id: string }>(items: T[]): T[] {
  return [...items].sort(compareNumericIds);
}

/**
 * Reads the persistent high-water mark counter for members from localStorage.
 */
export function getStoredMemberCounter(): number {
  if (typeof window === "undefined") return 0;
  try {
    const raw = localStorage.getItem(MEMBER_ID_COUNTER_KEY);
    return raw ? parseInt(raw, 10) || 0 : 0;
  } catch {
    return 0;
  }
}

/**
 * Reads the persistent high-water mark counter for staff from localStorage.
 */
export function getStoredStaffCounter(): number {
  if (typeof window === "undefined") return 0;
  try {
    const raw = localStorage.getItem(STAFF_ID_COUNTER_KEY);
    return raw ? parseInt(raw, 10) || 0 : 0;
  } catch {
    return 0;
  }
}

/**
 * Updates the persistent high-water mark counter if the provided number is higher.
 */
export function updateMemberCounterHighWaterMark(idOrNumber: string | number): void {
  if (typeof window === "undefined") return;
  const num = typeof idOrNumber === "number" ? idOrNumber : extractNumericSuffix(idOrNumber);
  if (num <= 0) return;
  try {
    const current = getStoredMemberCounter();
    if (num > current) {
      localStorage.setItem(MEMBER_ID_COUNTER_KEY, String(num));
    }
  } catch {
    // Ignore localStorage write failures in restricted environments
  }
}

/**
 * Updates the persistent high-water mark counter for staff if higher.
 */
export function updateStaffCounterHighWaterMark(idOrNumber: string | number): void {
  if (typeof window === "undefined") return;
  const num = typeof idOrNumber === "number" ? idOrNumber : extractNumericSuffix(idOrNumber);
  if (num <= 0) return;
  try {
    const current = getStoredStaffCounter();
    if (num > current) {
      localStorage.setItem(STAFF_ID_COUNTER_KEY, String(num));
    }
  } catch {
    // Ignore localStorage write failures
  }
}

/**
 * Generates the next sequential Member ID (e.g. "GYM008").
 *
 * Rules:
 * - Scans all current existing records for the highest numeric suffix.
 * - Compares with persistent high-water mark (so deleted IDs are NEVER reused).
 * - Ensures candidate ID is strictly unused.
 * - Advances and persists the high-water mark.
 */
export function getNextMemberId(
  existingRecords: Array<{ id: string }> = [],
  prefix: string = "GYM"
): string {
  const existingNumbers = existingRecords.map((r) => extractNumericSuffix(r.id));
  const maxInRecords = existingNumbers.length > 0 ? Math.max(...existingNumbers) : 0;
  const storedCounter = getStoredMemberCounter();

  // Baseline is highest of existing records and stored counter
  let nextNum = Math.max(maxInRecords, storedCounter) + 1;

  // Safety check: ensure nextNum is not already in existingRecords
  const existingIdSet = new Set(existingRecords.map((r) => r.id.toLowerCase()));
  while (existingIdSet.has(`${prefix.toLowerCase()}${String(nextNum).padStart(3, "0")}`)) {
    nextNum++;
  }

  // Update persistent counter to the newly issued number
  updateMemberCounterHighWaterMark(nextNum);

  return `${prefix}${String(nextNum).padStart(3, "0")}`;
}

/**
 * Generates a batch of sequential unique Member IDs for bulk import.
 */
export function generateNextMemberIds(
  count: number,
  existingRecords: Array<{ id: string }> = [],
  prefix: string = "GYM"
): string[] {
  if (count <= 0) return [];

  const existingNumbers = existingRecords.map((r) => extractNumericSuffix(r.id));
  const maxInRecords = existingNumbers.length > 0 ? Math.max(...existingNumbers) : 0;
  const storedCounter = getStoredMemberCounter();

  let nextNum = Math.max(maxInRecords, storedCounter) + 1;
  const existingIdSet = new Set(existingRecords.map((r) => r.id.toLowerCase()));

  const generated: string[] = [];
  for (let i = 0; i < count; i++) {
    while (existingIdSet.has(`${prefix.toLowerCase()}${String(nextNum).padStart(3, "0")}`)) {
      nextNum++;
    }
    const id = `${prefix}${String(nextNum).padStart(3, "0")}`;
    generated.push(id);
    existingIdSet.add(id.toLowerCase());
    nextNum++;
  }

  const finalMax = nextNum - 1;
  updateMemberCounterHighWaterMark(finalMax);

  return generated;
}

/**
 * Generates the next sequential Staff ID (e.g. "STF008").
 *
 * Rules:
 * - Scans all current staff for the highest numeric suffix.
 * - Compares with persistent high-water mark (so deleted IDs are NEVER reused).
 * - Ensures candidate ID is strictly unused.
 * - Advances and persists the high-water mark.
 */
export function getNextStaffId(
  existingRecords: Array<{ id: string }> = [],
  prefix: string = "STF"
): string {
  const existingNumbers = existingRecords.map((r) => extractNumericSuffix(r.id));
  const maxInRecords = existingNumbers.length > 0 ? Math.max(...existingNumbers) : 0;
  const storedCounter = getStoredStaffCounter();

  let nextNum = Math.max(maxInRecords, storedCounter) + 1;

  const existingIdSet = new Set(existingRecords.map((r) => r.id.toLowerCase()));
  while (existingIdSet.has(`${prefix.toLowerCase()}${String(nextNum).padStart(3, "0")}`)) {
    nextNum++;
  }

  updateStaffCounterHighWaterMark(nextNum);

  return `${prefix}${String(nextNum).padStart(3, "0")}`;
}

