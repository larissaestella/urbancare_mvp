import { useEffect, useState, type FormEvent } from "react";
import { call } from "./api";
import { Button, Plate, StatusShape } from "./ui";
import "./landing.css";

// Copy verbatim do docx Sprint 2 (Smoke Test + CTA), sem os colchetes do botão.
const HEADLINE = "Reduza em até 9% os custos de frota ociosa com monitoramento IoT em tempo real";
const SUBHEADLINE = "Teste o UrbanFlow sem custo por 30 dias em até 3 pontos críticos da sua concessionária.";
const MICROCOPY = "✓ Instalação rápida em 48h · 100% em conformidade com a LGPD · Sem fidelidade contratual";
export const CTA = { A: "QUERO SOLICITAR O PILOTO GRATUITO →", B: "AGENDAR DEMONSTRAÇÃO TÉCNICA DO PAINEL CCO (15 MIN) →" } as const;
const NEXT = { A: "a instalação do lote piloto", B: "a demonstração técnica do painel CCO" } as const;
type Variant = keyof typeof CTA;

function stored(key: string, make: () => string): string {
  try {
    const v = localStorage.getItem(key) ?? make();
    localStorage.setItem(key, v);
    return v;
  } catch {
    return make();
  }
}

/** Variante sorteada e fixa por navegador; `?v=A` ou `?v=B` força uma delas (para mostrar as duas na demo). */
function assign(): { visitor: string; variant: Variant } {
  const forced = new URLSearchParams(location.search).get("v")?.toUpperCase();
  const variant = forced === "A" || forced === "B" ? forced : stored("uf.variant", () => (Math.random() < 0.5 ? "A" : "B"));
  return { visitor: stored("uf.visitor", () => crypto.randomUUID()), variant: variant as Variant };
}

export default function Landing() {
  const [{ visitor, variant }] = useState(assign);
  const [step, setStep] = useState<"cta" | "form" | "done">("cta");
  const track = (kind: "visit" | "click") => call("POST", "/landing/events", { visitor, variant, kind }).catch(() => {});

  useEffect(() => { track("visit"); }, []);

  return (
    <main className="lp">
      <section className="lp__pitch">
        <div className="lp__logo">
          <svg viewBox="0 0 32 32" aria-hidden="true">
            <rect width="32" height="32" rx="2" fill="var(--signal-yellow)" />
            <path d="M10 7h12v11H14v7h-4z" fill="var(--totem-ink)" /><rect x="14" y="10" width="5" height="2" fill="var(--signal-yellow)" />
            <rect x="14" y="14" width="5" height="2" fill="var(--signal-yellow)" />
          </svg>
          <span>UrbanFlow</span>
        </div>
        <h1 className="lp__headline">{HEADLINE}</h1>
        <p className="lp__sub">{SUBHEADLINE}</p>
        {step === "cta" && (
          <button className="btn btn--primary lp__cta" onClick={() => { track("click"); setStep("form"); }}>{CTA[variant]}</button>
        )}
        {step === "form" && <LeadForm visitor={visitor} variant={variant} onDone={() => setStep("done")} />}
        {step === "done" && (
          <div className="lp__done" role="status">
            <StatusShape status="normal" color="var(--status-green)" />
            <span>Recebemos seu pedido. Vamos responder no e-mail informado para agendar {NEXT[variant]}.</span>
          </div>
        )}
        <p className="lp__micro">{MICROCOPY}</p>
      </section>
      <Plate title="Painel operacional em tempo real · 45 s">
        <video className="lp__video" controls muted playsInline preload="metadata" poster="/video/urbanflow-45s.jpg"
          aria-label="Vídeo demonstrativo de 45 segundos: alerta, envio do ônibus extra e fila esvaziando">
          <source src="/video/urbanflow-45s.mp4" type="video/mp4" />
        </video>
      </Plate>
    </main>
  );
}

function LeadForm({ visitor, variant, onDone }: { visitor: string; variant: Variant; onDone: () => void }) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const r = await fetch("/api/leads", { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ visitor, variant, company: f.get("company"), size: Number(f.get("size")), email: f.get("email") }) });
      if (r.ok) return onDone();
      const msg = JSON.stringify(await r.json().catch(() => ""));
      setError(msg.includes("corporativo") ? "Use o e-mail corporativo." : msg.includes("email") ? "Confira o e-mail." : "Confira os campos.");
    } catch {
      setError("Não foi possível enviar. Tente de novo.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="lp__form" onSubmit={submit}>
      <label><span className="t-overline">Empresa / concessionária</span><input name="company" required minLength={2} autoComplete="organization" /></label>
      <label><span className="t-overline">Quantidade estimada de linhas / pontos</span><input name="size" type="number" min={1} required inputMode="numeric" /></label>
      <label><span className="t-overline">E-mail corporativo</span><input name="email" type="email" required autoComplete="email" /></label>
      {error && <p className="lp__error" role="alert">{error}</p>}
      <Button disabled={busy}>Enviar</Button>
    </form>
  );
}
