"use client";

import { useEffect, useState } from "react";
import { THEME_STORAGE_KEY } from "@/lib/theme";

// Reads whatever layout.js's inline script already stamped onto <html data-theme="..."> before
// first paint, then lets the Sidebar's ThemeToggle flip it. Persisted to localStorage; light is the
// default whenever nothing is stored (see lib/theme.js — there is no OS-preference fallback).
export function useTheme() {
  const [theme, setThemeState] = useState("light");

  useEffect(() => {
    setThemeState(document.documentElement.getAttribute("data-theme") || "light");
  }, []);

  function setTheme(next) {
    setThemeState(next);
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // Storage blocked (private mode, etc.) — theme still applies for this page load, just won't persist.
    }
  }

  return { theme, setTheme, toggleTheme: () => setTheme(theme === "dark" ? "light" : "dark") };
}
