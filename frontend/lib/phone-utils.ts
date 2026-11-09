/**
 * Phone number validation and formatting utilities for GYMCORE
 * Standard Indian mobile numbers: 10 digits starting with 6, 7, 8, or 9
 */

/**
 * Extracts raw 10-digit mobile number by removing country code, leading zero, spaces, dashes
 */
export function sanitizeIndianMobile(input: string): string {
  if (!input) return "";
  let digits = input.replace(/\D/g, "");

  // If starts with 91 and has 12 digits, strip country code 91
  if (digits.length === 12 && digits.startsWith("91")) {
    digits = digits.slice(2);
  }

  // If starts with 0 and has 11 digits, strip leading 0
  if (digits.length === 11 && digits.startsWith("0")) {
    digits = digits.slice(1);
  }

  return digits;
}

/**
 * Validates whether the given string is a valid 10-digit Indian mobile number
 * Valid prefixes in India: 6, 7, 8, 9
 */
export function isValidIndianMobile(input: string): boolean {
  const digits = sanitizeIndianMobile(input);
  return /^[6-9]\d{9}$/.test(digits);
}

/**
 * Formats a phone number consistently as +91 XXXXX XXXXX
 * If invalid or incomplete, formats as much as possible cleanly
 */
export function formatIndianMobile(input: string): string {
  if (!input) return "";
  const digits = sanitizeIndianMobile(input);

  if (digits.length === 10) {
    return `+91 ${digits.slice(0, 5)} ${digits.slice(5)}`;
  }

  // If already formatted with country code and valid
  if (input.startsWith("+91") && digits.length === 10) {
    return `+91 ${digits.slice(0, 5)} ${digits.slice(5)}`;
  }

  // Fallback for partial input during typing
  if (digits.length > 5) {
    return `+91 ${digits.slice(0, 5)} ${digits.slice(5, 10)}`;
  }

  if (digits.length > 0) {
    return `+91 ${digits}`;
  }

  return input;
}

