import { type ReactNode } from "react";
import { useInView } from "../../lib/motion";

interface Props {
  children: ReactNode;
  delayMs?: number;
  className?: string;
  as?: "div" | "section" | "li" | "span";
}

/** Scroll-reveal wrapper: fades/rises once when entering the viewport. */
export function Reveal({ children, delayMs = 0, className = "", as = "div" }: Props) {
  const [ref, inView] = useInView<HTMLDivElement>();
  const Tag = as as "div";
  return (
    <Tag
      ref={ref}
      className={`reveal ${inView ? "reveal--in" : ""} ${className}`}
      style={{ ["--reveal-delay" as string]: `${delayMs}ms` }}
    >
      {children}
    </Tag>
  );
}
