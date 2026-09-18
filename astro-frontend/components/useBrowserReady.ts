"use client";

import { useSyncExternalStore } from "react";

const subscribe = () => () => {};
/** Match server markup, then expose browser-only APIs after hydration. */
export function useBrowserReady() {
  return useSyncExternalStore(subscribe, () => true, () => false);
}
