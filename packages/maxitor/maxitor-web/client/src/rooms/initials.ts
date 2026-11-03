// src/rooms/initials.ts

/** The letters on a participant's circle: first letters of the first two words, else the first two letters. */
export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  const letters = words.length > 1 ? [...words[0]][0] + [...words[1]][0] : [...words[0]].slice(0, 2).join("");
  return letters.toUpperCase();
}

/** Text colour on a filled circle: dark on light fills, white on dark ones (WCAG relative luminance). */
export function inkOn(hex: string): string {
  const n = Number.parseInt(hex.replace("#", ""), 16);
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((channel) => {
    const c = channel / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.4 ? "#0f172a" : "#ffffff";
}
