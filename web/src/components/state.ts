// DESIGN.md section 2's five states: background, text, icon and border, with the lucide icon
// each one uses. Alerts and badges read their look from here, so a state looks the same
// wherever it appears.
import { Check, CircleDashed, CircleX, Info, TriangleAlert, type LucideIcon } from "lucide-react";

export type State = "info" | "success" | "warning" | "error" | "neutral";

export const STATES: Record<State, { box: string; text: string; icon: string; border: string; Icon: LucideIcon }> = {
  info: { box: "bg-info-bg", text: "text-info", icon: "text-info-icon", border: "border-info-icon", Icon: Info },
  success: { box: "bg-success-bg", text: "text-success", icon: "text-success", border: "border-success", Icon: Check },
  warning: {
    box: "bg-warning-bg",
    text: "text-warning",
    icon: "text-warning-icon",
    border: "border-warning-icon",
    Icon: TriangleAlert,
  },
  error: { box: "bg-error-bg", text: "text-error", icon: "text-error-icon", border: "border-error-icon", Icon: CircleX },
  neutral: {
    box: "bg-neutral-bg",
    text: "text-neutral",
    icon: "text-line-strong",
    border: "border-line-strong",
    Icon: CircleDashed,
  },
};
