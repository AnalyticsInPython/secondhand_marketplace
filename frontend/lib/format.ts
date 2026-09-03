import type { CSSProperties } from "react";

import type { Category, Condition, ListingCard, ListingStatus } from "./types";

export const CATEGORY_LABELS: Record<Category, string> = {
  furniture: "Furniture",
  textbooks: "Textbooks",
  electronics: "Electronics",
  kitchen_home: "Kitchen & home",
  clothing: "Clothing",
  bikes_transport: "Bikes & transport",
  sports: "Sports",
  free_stuff: "Free stuff",
};

export const CONDITION_LABELS: Record<Condition, string> = {
  new: "New",
  like_new: "Like new",
  used_good: "Used — good",
  used_fair: "Used — fair",
};

export const SUBCATEGORY_LABELS: Record<string, string> = {
  desks: "Desks",
  chairs: "Chairs",
  beds_mattresses: "Beds & mattresses",
  storage_shelving: "Storage & shelving",
  sofas_tables: "Sofas & tables",
};

export const STATUS_LABELS: Record<ListingStatus, string> = {
  draft: "Draft",
  active: "On sale",
  reserved: "Reserved",
  sold: "Sold",
  delisted: "Delisted",
};

export function price(cents: number, isFree: boolean): string {
  if (isFree || cents === 0) return "Free";
  return `$${(cents / 100).toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

/** "10027 · 0.3 mi · 12 min ago" — the card's metadata line. */
export function cardMeta(item: ListingCard): string {
  const parts = [item.zip_code];
  if (item.distance_mi !== null) parts.push(`${item.distance_mi.toFixed(1)} mi`);
  parts.push(relativeTime(item.posted_at));
  return parts.join(" · ");
}

export function relativeTime(iso: string): string {
  const seconds = (Date.now() - new Date(iso).getTime()) / 1000;
  if (seconds < 60) return "just now";
  const units: [number, string][] = [
    [60, "min"],
    [3600, "hour"],
    [86400, "day"],
    [604800, "week"],
  ];
  for (let i = units.length - 1; i >= 0; i--) {
    const [size, name] = units[i];
    if (seconds >= size) {
      const n = Math.floor(seconds / size);
      return `${n} ${name}${n > 1 ? "s" : ""} ago`;
    }
  }
  return "just now";
}

export function absoluteDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

/**
 * Seeded listings have no photos, so the feed draws the same gradient the Figma
 * mockups use. Derived from the id, so a given listing always looks the same.
 */
const GRADIENTS: [string, string][] = [
  ["#dce9f5", "#9fc2e0"],
  ["#f1e4d2", "#d9be94"],
  ["#e4e8f0", "#b9c3d6"],
  ["#ddede4", "#a8cfbb"],
  ["#f3e1e1", "#ddb6b6"],
  ["#e8e2f2", "#bfb2dc"],
  ["#eaeaea", "#c4c4c4"],
];

export function placeholderGradient(id: string): CSSProperties {
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  const [from, to] = GRADIENTS[hash % GRADIENTS.length];
  // Custom properties are not in CSSProperties, hence the cast.
  return { "--ph-from": from, "--ph-to": to } as unknown as CSSProperties;
}
