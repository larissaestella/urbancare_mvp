import type { ReactNode } from "react";
import "./ui.css";

export type Status = "normal" | "atencao" | "critico";
const LABEL: Record<Status, string> = { normal: "Normal", atencao: "Atenção", critico: "Crítico" };

/** Forma desenhada do status: círculo normal, triângulo atenção, quadrado crítico. */
export function StatusShape({ status, color, size = 10 }: { status: Status; color: string; size?: number }) {
  const s = size;
  return (
    <svg className="shape" width={s} height={s} viewBox="0 0 10 10" aria-hidden="true">
      {status === "normal" && <circle cx="5" cy="5" r="4.5" fill={color} />}
      {status === "atencao" && <polygon points="5,0.5 9.8,9.5 0.2,9.5" fill={color} />}
      {status === "critico" && <rect x="0.5" y="0.5" width="9" height="9" fill={color} />}
    </svg>
  );
}

const PILL_SHAPE: Record<Status, string> = { normal: "#fff", atencao: "var(--totem-ink)", critico: "#fff" };

export function StatusPill({ status }: { status: Status }) {
  return (
    <span className={`pill pill--${status}`}>
      <StatusShape status={status} color={PILL_SHAPE[status]} />
      {LABEL[status]}
    </span>
  );
}

export function LivePill({ children = "Ao vivo" }: { children?: ReactNode }) {
  return (
    <span className="pill pill--aovivo">
      <StatusShape status="normal" color="var(--status-green-on-ink)" />
      {children}
    </span>
  );
}

export function HighlightPill({ children }: { children: ReactNode }) {
  return (
    <span className="pill pill--destaque">
      <StatusShape status="normal" color="#fff" />
      {children}
    </span>
  );
}

export const LineChip = ({ line }: { line: string }) => <span className="chip">{line}</span>;

export function Plate({ title, right, critical, children }: { title: string; right?: ReactNode; critical?: boolean; children: ReactNode }) {
  return (
    <section className={`plate${critical ? " plate--crit" : ""}`}>
      <header className={`plate__band${critical ? " plate__band--crit" : ""}`}>
        <h2 className="t-title">{title}</h2>
        {right}
      </header>
      <div className="plate__body">{children}</div>
    </section>
  );
}

export function TitlePlate({ title, meta, right }: { title: string; meta?: ReactNode; right?: ReactNode }) {
  return (
    <header className="title-plate">
      <div>
        <h1 className="t-display">{title}</h1>
        {meta && <p className="title-plate__meta">{meta}</p>}
      </div>
      {right}
    </header>
  );
}

export function Button({ variant = "primary", ...p }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" }) {
  return <button {...p} className={`btn btn--${variant}`} />;
}

export function Toggle({ on, onChange, label }: { on: boolean; onChange: (v: boolean) => void; label: string }) {
  return <button role="switch" aria-checked={on} aria-label={label} className="toggle" onClick={() => onChange(!on)} />;
}

export function Segmented<T extends string>({ options, value, onChange }: { options: T[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="segmented" role="group">
      {options.map((o) => (
        <button key={o} aria-pressed={o === value} onClick={() => onChange(o)}>{o}</button>
      ))}
    </div>
  );
}

export type Delta = "pos" | "neg" | "warn" | "neutral" | "info";
export function KpiStrip({ cells }: { cells: { label: string; value: string; delta: string; tone: Delta }[] }) {
  return (
    <div className="kpi-strip">
      {cells.map((c) => (
        <div className="kpi-cell" key={c.label}>
          <div className="t-overline kpi-cell__label">{c.label}</div>
          <div className="t-kpi">{c.value}</div>
          <div className={`t-caption kpi-cell__delta--${c.tone}`}>{c.delta}</div>
        </div>
      ))}
    </div>
  );
}

export function Sidebar({ items, active }: { items: string[]; active: string }) {
  return (
    <aside className="totem">
      <div className="totem__logo"><span className="totem__mark" /><span className="t-title">UrbanFlow</span></div>
      <div className="t-overline totem__group">Operação</div>
      <nav className="totem__nav">
        {items.map((i) => (
          <button key={i} className="nav-item" aria-current={i === active ? "page" : undefined}>
            <span className="nav-item__dot" />{i}
          </button>
        ))}
      </nav>
      <div className="privacy">
        <svg width="14" height="16" viewBox="0 0 14 16" aria-hidden="true">
          <rect x="1" y="7" width="12" height="8" fill="#fff" />
          <path d="M3.5 7V5a3.5 3.5 0 0 1 7 0v2" fill="none" stroke="#fff" strokeWidth="1.6" />
        </svg>
        <span className="t-small-strong">Contagem anônima</span>
      </div>
    </aside>
  );
}
