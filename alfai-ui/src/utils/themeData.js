// src/utils/themeData.js
export const themes = [
  { background: "#1A1A2E", color: "#FFFFFF", primaryColor: "#0F3460" },
  { background: "#461220", color: "#FFFFFF", primaryColor: "#E94560" },
  { background: "#192A51", color: "#FFFFFF", primaryColor: "#967AA1" },
  { background: "#F7B267", color: "#000000", primaryColor: "#F4845F" },
  { background: "#F25F5C", color: "#000000", primaryColor: "#642B36" },
  { background: "#231F20", color: "#FFF", primaryColor: "#BB4430" },
];

export const applyTheme = (theme) => {
  const root = document.documentElement;
  root.style.setProperty("--background", theme.background);
  root.style.setProperty("--color", theme.color);
  root.style.setProperty("--primary-color", theme.primaryColor);
};