// Disclosure (ticket 126, the tuck-away inventory's Collapsible call; DESIGN.md section 5): method a reader opens once,
// such as "How these checks work" or "How I dated the steps", closed in place behind a flush ghost button with
// aria-expanded and aria-controls. The button keeps its words open or closed, so it stays where it was and keeps focus;
// its chevron turns, as the answer's "Show the steps I took" does.
import { useId, useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { cx } from "../lib/cx";
import { Button } from "./Button";

export function Disclosure({ label, children, onPage = false, className }: { label: ReactNode; children: ReactNode; onPage?: boolean; className?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div data-disclosure={open ? "open" : "closed"} className={className}>
      <Button
        variant="ghost"
        flush
        onPage={onPage}
        icon={ChevronDown}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen(!open)}
        className={cx("[&>svg]:transition-transform", open && "[&>svg]:rotate-180")}
      >
        {label}
      </Button>
      <div id={id} hidden={!open} className="mt-2 max-w-prose">
        {children}
      </div>
    </div>
  );
}
