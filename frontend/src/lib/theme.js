export const THEME_STORAGE_KEY = "opsflow-theme";

// Inline script text, injected into <head> by layout.js and run before first paint — reads the
// stored preference and stamps data-theme on <html> synchronously so there's no flash of the wrong
// theme. Defaults to "light" if nothing is stored yet (first visit, or storage blocked) — this is
// the actual default, not a fallback for a missing OS-preference block (that block was removed:
// light must be the default regardless of the visitor's system setting).
export const THEME_INIT_SCRIPT = `
(function () {
  try {
    var stored = localStorage.getItem("${THEME_STORAGE_KEY}");
    document.documentElement.setAttribute("data-theme", stored === "dark" ? "dark" : "light");
  } catch (e) {
    document.documentElement.setAttribute("data-theme", "light");
  }
})();
`;
