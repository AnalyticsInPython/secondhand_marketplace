/**
 * The shared primitives — UX_SPEC.md §3.4.
 *
 * Every screen is built from these, so a change here is a change everywhere.
 * Colours come from the tokens in globals.css; there are no raw hex values
 * below and there should not be.
 */

"use client";

import type { ReactNode } from "react";

function cx(...parts: (string | false | undefined | null)[]): string {
  return parts.filter(Boolean).join(" ");
}

// ---------------------------------------------------------------- Button

type ButtonProps = {
  children: ReactNode;
  variant?: "primary" | "ghost" | "danger";
  full?: boolean;
  disabled?: boolean;
  icon?: ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
};

export function Button({
  children,
  variant = "primary",
  full,
  disabled,
  icon,
  onClick,
  type = "button",
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-[12px] px-5 py-3.5 text-[15px] font-semibold transition-colors";
  const styles = {
    primary: "bg-deep text-white hover:bg-primary",
    ghost: "bg-surface text-ink border border-line-strong hover:bg-muted",
    danger: "bg-surface text-danger border border-danger hover:bg-danger/5",
  }[variant];

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={cx(
        base,
        disabled ? "bg-muted text-ink3 border border-line cursor-not-allowed" : styles,
        full && "w-full",
      )}
    >
      {icon}
      {children}
    </button>
  );
}

// ---------------------------------------------------------------- Field

type FieldProps = {
  label: string;
  children: ReactNode;
  hint?: string;
  error?: string;
  /** Renders the grey OPTIONAL tag. Phone is the one that uses it (§5.1). */
  optional?: boolean;
  locked?: boolean;
};

export function Field({ label, children, hint, error, optional, locked }: FieldProps) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span className="text-[13px] font-semibold text-ink2">{label}</span>
        {optional && <Tag>OPTIONAL</Tag>}
        {locked && <Tag>LOCKED</Tag>}
      </div>
      {children}
      {error ? (
        <p className="text-[12px] text-danger">{error}</p>
      ) : hint ? (
        <p className="text-[12px] leading-[18px] text-ink3">{hint}</p>
      ) : null}
    </div>
  );
}

export function Tag({ children }: { children: ReactNode }) {
  return (
    <span className="rounded-full bg-muted px-1.5 py-0.5 text-[9.5px] font-semibold tracking-[0.02em] text-ink2">
      {children}
    </span>
  );
}

// ---------------------------------------------------------------- Input

type InputProps = {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  state?: "default" | "focus" | "error" | "ok";
  disabled?: boolean;
  left?: ReactNode;
  right?: ReactNode;
  type?: string;
};

export function Input({
  value,
  onChange,
  placeholder,
  state = "default",
  disabled,
  left,
  right,
  type = "text",
}: InputProps) {
  const border = {
    default: "border-line-strong",
    focus: "border-deep border-[1.5px]",
    error: "border-danger border-[1.5px]",
    ok: "border-ok border-[1.5px]",
  }[state];

  return (
    <div
      className={cx(
        "flex items-center gap-2.5 rounded-[10px] border px-4 py-3.5",
        disabled ? "bg-muted" : "bg-surface",
        border,
      )}
    >
      {left}
      <input
        type={type}
        value={value}
        disabled={disabled}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-transparent text-[15px] font-medium text-ink outline-none placeholder:font-normal placeholder:text-ink3 disabled:text-ink2"
      />
      {right}
    </div>
  );
}

// ---------------------------------------------------------------- Select

type SelectProps = {
  value: string;
  onChange: (v: string) => void;
  children: ReactNode;
  placeholder?: string;
  state?: "default" | "error" | "ok";
  disabled?: boolean;
};

/** A native select in the Input's clothes. Fixed vocabularies only — never free text. */
export function Select({ value, onChange, children, placeholder, state = "default", disabled }: SelectProps) {
  const border = {
    default: "border-line-strong",
    error: "border-danger border-[1.5px]",
    ok: "border-ok border-[1.5px]",
  }[state];
  return (
    <div
      className={cx(
        "flex items-center rounded-[10px] border px-4 py-3.5",
        disabled ? "bg-muted" : "bg-surface",
        border,
      )}
    >
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className={cx(
          "w-full cursor-pointer bg-transparent text-[15px] font-medium outline-none",
          value ? "text-ink" : "text-ink3",
        )}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {children}
      </select>
    </div>
  );
}

// ---------------------------------------------------------------- Chip

export function Chip({
  children,
  active,
  onClick,
}: {
  children: ReactNode;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cx(
        "rounded-full px-3.5 py-2 text-[13px] transition-colors",
        active
          ? "bg-deep font-semibold text-white"
          : "border border-line bg-surface font-medium text-ink2 hover:bg-muted",
      )}
    >
      {children}
    </button>
  );
}

// ---------------------------------------------------------------- Badge

/**
 * A match badge. Only ever rendered from the `badges` array the API returns —
 * never derived on the client by comparing attributes, because the client is
 * not given the attributes to compare (UX_SPEC.md §5.3).
 */
export function MatchBadge({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-tint px-2.5 py-1 text-[9.5px] font-semibold tracking-[0.02em] text-deep">
      <ShieldIcon className="h-2.5 w-2.5" />
      {children}
    </span>
  );
}

// ---------------------------------------------------------------- Toggle

export function Toggle({ on, onChange }: { on: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      onClick={() => onChange(!on)}
      className={cx(
        "flex h-6 w-[42px] shrink-0 items-center rounded-full p-[3px] transition-colors",
        on ? "justify-end bg-deep" : "justify-start bg-line-strong",
      )}
    >
      <span className="h-[18px] w-[18px] rounded-full bg-white" />
    </button>
  );
}

export function Checkbox({ on, onChange }: { on: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={on}
      onClick={() => onChange(!on)}
      className={cx(
        "flex h-[19px] w-[19px] shrink-0 items-center justify-center rounded-[5px] border",
        on ? "border-deep bg-deep" : "border-line-strong bg-surface",
      )}
    >
      {on && <CheckIcon className="h-3 w-3 text-white" />}
    </button>
  );
}

// ---------------------------------------------------------------- Segmented

export function Segmented<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex gap-1.5 rounded-[12px] border border-line bg-muted p-1">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={cx(
            "flex-1 rounded-[9px] px-3 py-2.5 text-[13.5px] transition-colors",
            o.value === value
              ? "bg-surface font-semibold text-deep shadow-sm"
              : "font-medium text-ink2",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------- Card

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cx("rounded-[16px] border border-line bg-surface", className)}>{children}</div>
  );
}

/**
 * The removable variant of Chip (UX_SPEC.md §3.4).
 *
 * Used for the active-filter summary above the feed: every chip names one
 * filter that is narrowing what you see, and clearing it is one tap.
 */
export function RemovableChip({
  label,
  onRemove,
}: {
  label: string;
  onRemove: () => void;
}) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-tint py-1 pl-3 pr-1 text-[12.5px] font-semibold text-deep">
      {label}
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove filter: ${label}`}
        className="grid h-[19px] w-[19px] place-items-center rounded-full transition-colors hover:bg-deep hover:text-white"
      >
        <svg
          viewBox="0 0 24 24"
          className="h-3 w-3"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.6"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <path d="M6 6l12 12M18 6L6 18" />
        </svg>
      </button>
    </span>
  );
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="text-[11px] font-semibold tracking-[0.08em] text-ink2">{children}</p>
  );
}

// ---------------------------------------------------------------- Icons
// Inline so there is no icon dependency. 24×24, 1.8 stroke (UX_SPEC.md §3.3).

type IconProps = { className?: string };
const stroke = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function ShieldIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className ?? "h-4 w-4"} {...stroke}>
      <path d="M12 2.5l8 3.2v6.1c0 5-3.4 8.7-8 9.7-4.6-1-8-4.7-8-9.7V5.7l8-3.2z" />
      <path d="M8.5 12l2.5 2.5 4.5-5" />
    </svg>
  );
}

export function CheckIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className ?? "h-4 w-4"} {...stroke} strokeWidth={3}>
      <path d="M20 6L9 17l-5-5" />
    </svg>
  );
}

export function MailIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className ?? "h-[18px] w-[18px]"} {...stroke}>
      <rect x="2.5" y="5" width="19" height="14" rx="2.5" />
      <path d="M3 7l9 6 9-6" />
    </svg>
  );
}

export function SmsIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className ?? "h-[18px] w-[18px]"} {...stroke}>
      <rect x="3" y="4.5" width="18" height="12.5" rx="3" />
      <path d="M7.6 20.5l1.4-3.5M8 9.3h8M8 12.8h5" />
    </svg>
  );
}

export function PinIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className ?? "h-4 w-4"} {...stroke}>
      <path d="M12 22s7-6.3 7-11a7 7 0 10-14 0c0 4.7 7 11 7 11z" />
      <circle cx="12" cy="11" r="2.6" />
    </svg>
  );
}

export function SearchIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className ?? "h-[18px] w-[18px]"} {...stroke} strokeWidth={2}>
      <circle cx="11" cy="11" r="7" />
      <path d="M20.5 20.5L16.2 16.2" />
    </svg>
  );
}

export function HeartIcon({ className, filled }: IconProps & { filled?: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className ?? "h-[18px] w-[18px]"}
      {...stroke}
      fill={filled ? "currentColor" : "none"}
    >
      <path d="M12 20.5S3.5 15.3 3.5 9.6A4.6 4.6 0 0112 7a4.6 4.6 0 018.5 2.6c0 5.7-8.5 10.9-8.5 10.9z" />
    </svg>
  );
}

export function XIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className ?? "h-4 w-4"} {...stroke} strokeWidth={2.2}>
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

export function CameraIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className ?? "h-5 w-5"} {...stroke}>
      <path d="M3.5 8.5A2.5 2.5 0 016 6h2l1.2-2h5.6L16 6h2a2.5 2.5 0 012.5 2.5v8A2.5 2.5 0 0118 19H6a2.5 2.5 0 01-2.5-2.5v-8z" />
      <circle cx="12" cy="12.5" r="3.5" />
    </svg>
  );
}

export function ShareIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className ?? "h-[18px] w-[18px]"} {...stroke}>
      <circle cx="18" cy="5" r="2.5" />
      <circle cx="6" cy="12" r="2.5" />
      <circle cx="18" cy="19" r="2.5" />
      <path d="M8.2 10.8l7.6-4.4M8.2 13.2l7.6 4.4" />
    </svg>
  );
}

export function ChevronLeftIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className ?? "h-4 w-4"} {...stroke} strokeWidth={2.2}>
      <path d="M15 5l-7 7 7 7" />
    </svg>
  );
}

export function PlusIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className ?? "h-4 w-4"} {...stroke} strokeWidth={2.2}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}
