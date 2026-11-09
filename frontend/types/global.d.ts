/* eslint-disable @typescript-eslint/no-explicit-any */
declare module "next" {
  export interface Metadata {
    title?: string;
    description?: string;
    [key: string]: any;
  }
  export interface NextConfig {
    [key: string]: any;
  }
}

declare module "next/link" {
  const Link: any;
  export default Link;
}

declare module "next/navigation" {
  export function usePathname(): string;
  export function useRouter(): any;
  export function useSearchParams(): URLSearchParams;
  export function useParams(): Record<string, string | string[]>;
}

declare module "next/types.js" {
  export type Route = string;
  export type ResolvingMetadata = any;
  export type ResolvingViewport = any;
  export type Metadata = any;
}

declare module "next/dist/lib/metadata/types/metadata-interface.js" {
  export type Metadata = any;
  export type ResolvingMetadata = any;
  export type ResolvingViewport = any;
}

declare module "next/dist/build/segment-config/app/app-segment-config.js" {
  export type AppSegmentConfig = any;
  export type InstantConfigForTypeCheckInternal = any;
  export type Prefetch = any;
  export type EnsureStatic = any;
}
