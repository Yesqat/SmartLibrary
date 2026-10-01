"use client";

import { useEffect, useSyncExternalStore } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  checkSession,
  clearSession,
  getAuthState,
  getServerAuthState,
  refreshSession,
  subscribeAuth,
} from "@/services/api-client";

export function useAuth() {
  return useSyncExternalStore(subscribeAuth, getAuthState, getServerAuthState);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const cache = useQueryClient();
  useEffect(() => {
    const identityKey = () => {
      const user = getAuthState().user;
      return user ? `${user.id}:${user.role}:${user.status}` : null;
    };
    let identity = identityKey();
    const unsubscribe = subscribeAuth(() => {
      const next = identityKey();
      if (identity !== next) cache.clear();
      identity = next;
    });
    void refreshSession().catch(() => undefined);
    const check = () => {
      if (document.visibilityState === "visible")
        void checkSession().catch(() => undefined);
    };
    window.addEventListener("focus", check);
    const interval = window.setInterval(check, 60_000);
    const channel =
      typeof BroadcastChannel !== "undefined"
        ? new BroadcastChannel("smartlibrary-auth")
        : null;
    if (channel)
      channel.onmessage = (event: MessageEvent<unknown>) => {
        if (event.data === "logout") clearSession();
      };
    return () => {
      unsubscribe();
      window.removeEventListener("focus", check);
      window.clearInterval(interval);
      channel?.close();
    };
  }, [cache]);
  return children;
}
