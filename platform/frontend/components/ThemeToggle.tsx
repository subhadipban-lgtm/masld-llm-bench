"use client";

/** Dark-mode toggle: class strategy + localStorage persistence. */

export function ThemeToggle() {
  const onClick = () => {
    const el = document.documentElement;
    const next = el.classList.toggle("dark");
    localStorage.theme = next ? "dark" : "light";
  };
  return (
    <button
      onClick={onClick}
      aria-label="Toggle dark mode"
      className="rounded-md border border-neutral-300 px-2 py-1 text-sm dark:border-neutral-700"
    >
      ◐
    </button>
  );
}
