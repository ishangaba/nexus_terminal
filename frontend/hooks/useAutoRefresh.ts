"use client";

import { useEffect, useRef } from "react";

/**
 * Calls `callback` on an interval, but only while the tab is visible — paused entirely
 * while backgrounded (so it never burns API calls on a tab nobody's looking at), and
 * fires one immediate refresh when the tab regains focus after being hidden.
 */
export function useAutoRefresh(callback: () => void, intervalMs: number) {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval> | null = null;

    function start() {
      if (intervalId) return;
      intervalId = setInterval(() => callbackRef.current(), intervalMs);
    }

    function stop() {
      if (intervalId) {
        clearInterval(intervalId);
        intervalId = null;
      }
    }

    function handleVisibilityChange() {
      if (document.visibilityState === "visible") {
        callbackRef.current();
        start();
      } else {
        stop();
      }
    }

    if (document.visibilityState === "visible") start();
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      stop();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [intervalMs]);
}
