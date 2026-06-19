import { useEffect, useState } from "react";

export function useTheme() {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem("pdf-rag-theme");
    if (saved) return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("pdf-rag-theme", theme);
  }, [theme]);

  return { theme, toggleTheme: () => setTheme((value) => (value === "dark" ? "light" : "dark")) };
}
