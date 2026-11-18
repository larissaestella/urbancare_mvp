import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { call } from "./api";
import "./address-registration.css";

type Address = {
  street: string;
  number: string;
  complement: string;
  neighborhood: string;
  city: string;
  state: string;
  postal_code: string;
};
type Extraction = { issuer: string; address: Address; confidence: number; perspective_corrected: boolean };
type Field = keyof Address;
type NearbyStop = { id: string; name: string; line: string; count: number; wait_min: number; status: string; enroute: boolean };
type SavedAddress = Address & { id: number; issuer: string; confirmed_at: string; nearby_stops: NearbyStop[] };
const STATUS_LABEL: Record<string, string> = { critico: "Lotação crítica", atencao: "Atenção", normal: "Normal" };

function visitorId(): string {
  try {
    const current = localStorage.getItem("uf.visitor") ?? crypto.randomUUID();
    localStorage.setItem("uf.visitor", current);
    return current;
  } catch {
    return crypto.randomUUID();
  }
}

const LABELS: Record<Field, string> = {
  street: "Rua / avenida",
  number: "Número",
  complement: "Complemento (opcional)",
  neighborhood: "Bairro",
  city: "Cidade",
  state: "UF",
  postal_code: "CEP",
};
const EMPTY: Address = { street: "", number: "", complement: "", neighborhood: "", city: "", state: "", postal_code: "" };

export default function AddressRegistration() {
  const [fileName, setFileName] = useState("");
  const [address, setAddress] = useState<Address | null>(null);
  const [issuer, setIssuer] = useState("");
  const [confidence, setConfidence] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [consent, setConsent] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<SavedAddress[] | null>(null);
  const [current, setCurrent] = useState<SavedAddress | null>(null);
  const [notice, setNotice] = useState("");
  const [visitor] = useState(visitorId);
  const base = `/citizens/${visitor}/addresses`;

  useEffect(() => {
    call<SavedAddress[]>("GET", base).then(setSaved).catch(() => setSaved([]));
  }, [base]);

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError("");
    setAddress(null);
    setConfirmed(false);
    setCurrent(null);
    setNotice("");
    setFileName(file.name);
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("Formato não suportado. Envie uma foto JPEG, PNG ou WEBP.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("A foto deve ter no máximo 10 MB.");
      return;
    }
    setBusy(true);
    try {
      const response = await fetch("/api/address/extract", { method: "POST", headers: { "content-type": file.type }, body: file });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Não foi possível ler o comprovante.");
      const extracted = result as Extraction;
      setAddress(extracted.address);
      setIssuer(extracted.issuer);
      setConfidence(extracted.confidence);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha na leitura. Tente outra foto.");
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  function update(field: Field, value: string) {
    setAddress((current) => current && { ...current, [field]: value });
    setConfirmed(false);
  }

  async function confirm(event: FormEvent) {
    event.preventDefault();
    if (!address || !canConfirm) return;
    setSaving(true);
    setError("");
    try {
      const response = await fetch(`/api${base}`, { method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ consent, issuer, ...address }) });
      const result = await response.json();
      if (!response.ok) throw new Error(response.status === 409 && typeof result.detail === "string" ? result.detail
        : "Não foi possível salvar o endereço. Revise os campos (UF com 2 letras, CEP com 8 dígitos) e tente de novo.");
      const created = result as SavedAddress;
      setCurrent(created);
      setSaved((list) => [created, ...(list ?? []).filter((item) => item.id !== created.id)]);
      setConfirmed(true);
      setNotice("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível salvar o endereço.");
    } finally {
      setSaving(false);
    }
  }

  async function remove(item: SavedAddress) {
    if (!window.confirm(`Excluir ${item.street}, ${item.number}?`)) return;
    try {
      await call("DELETE", `${base}/${item.id}`);
      setSaved((list) => (list ?? []).filter((other) => other.id !== item.id));
      if (current?.id === item.id) { setCurrent(null); setConfirmed(false); }
      setNotice("Endereço excluído do UrbanFlow.");
    } catch {
      setError("Não foi possível excluir agora. Tente novamente.");
    }
  }

  async function removeAll() {
    if (!window.confirm("Excluir todos os seus endereços cadastrados?")) return;
    try {
      await call("DELETE", base);
      setSaved([]);
      setCurrent(null);
      setConfirmed(false);
      setNotice("Todos os seus endereços foram excluídos do UrbanFlow.");
    } catch {
      setError("Não foi possível excluir agora. Tente novamente.");
    }
  }

  const required: Field[] = ["street", "number", "neighborhood", "city", "state", "postal_code"];
  const canConfirm = Boolean(consent && !saving && address && required.every((field) => address[field].trim()));

  return (
    <main className="address-page">
      <header className="address-header">
        <a className="address-brand" href="/" aria-label="UrbanFlow, início">
          <span className="address-brand__mark">U</span> UrbanFlow
        </a>
        <span className="address-header__tag">CADASTRO CIDADÃO</span>
      </header>
      <section className="address-content">
        <a className="address-back" href="/">← Voltar ao UrbanFlow</a>
        <p className="address-eyebrow">MVP CITIZENTECH · EXTRAÇÃO AUTOMÁTICA</p>
        <h1>Confirme seu endereço</h1>
        <p className="address-intro">Envie uma foto de uma conta Enel, Vivo ou Claro. O endereço de instalação será preenchido para você revisar.</p>

        <section className="address-card" aria-labelledby="upload-title">
          <div className="address-card__heading"><span className="address-step">1</span><h2 id="upload-title">Fotografe o comprovante</h2></div>
          <p>Enquadre a página inteira, com o texto legível e boa iluminação.</p>
          <label className="address-upload" htmlFor="address-file">
            <span className="address-upload__icon" aria-hidden="true">↑</span>
            <span><strong>{busy ? "Lendo comprovante…" : "Escolher foto"}</strong><small>JPEG, PNG ou WEBP · até 10 MB</small></span>
            <input id="address-file" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={upload} disabled={busy} />
          </label>
          {fileName && <p className="address-file" aria-live="polite">{fileName}</p>}
          {error && <p className="address-message address-message--error" role="alert">{error}</p>}
          <p className="address-privacy"><span aria-hidden="true">▣</span> Privacidade: foto processada em memória e descartada imediatamente. Nenhuma imagem é salva.</p>
        </section>

        {address && (
          <form className="address-card address-form" onSubmit={confirm}>
            <div className="address-card__heading"><span className="address-step">2</span><h2>Revise os dados extraídos</h2></div>
            <p className="address-source">Comprovante identificado: <strong>{issuer}</strong> · confiança OCR {Math.round(confidence * 100)}%</p>
            <div className="address-fields">
              {(["street", "number", "complement", "neighborhood", "city", "state", "postal_code"] as Field[]).map((field) => (
                <label key={field} className={`address-field address-field--${field}`}>
                  <span>{LABELS[field]}</span>
                  <input value={address[field]} maxLength={field === "street" ? 120 : 80}
                    required={field !== "complement"} autoComplete={field === "postal_code" ? "postal-code" : field === "street" ? "address-line1" : undefined}
                    onChange={(event) => update(field, event.target.value)} />
                </label>
              ))}
            </div>
            <p className="address-hint">O OCR pode errar. Confira e corrija os campos antes de continuar.</p>
            <label className="address-consent">
              <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
              <span>Autorizo o UrbanFlow a guardar somente este endereço para indicar os pontos de ônibus monitorados perto de mim. Posso excluí-lo a qualquer momento.</span>
            </label>
            <button type="submit" className="address-confirm" disabled={!canConfirm}>{saving ? "Salvando…" : "Confirmar endereço"}</button>
          </form>
        )}

        {confirmed && current && (
          <section className="address-card address-success" aria-live="polite">
            <span className="address-success__check" aria-hidden="true">✓</span>
            <div><h2>Endereço confirmado</h2>
              <p>{formatAddress(current)}</p>
              <small>Salvo no cadastro cidadão. A foto não foi guardada; nenhum nome ou documento é coletado.</small>
              <NearbyList stops={current.nearby_stops} />
            </div>
          </section>
        )}

        <section className="address-card" aria-labelledby="saved-title">
          <div className="address-card__heading"><span className="address-step">3</span><h2 id="saved-title">Meus endereços cadastrados</h2></div>
          {notice && <p className="address-message" role="status">{notice}</p>}
          {saved === null ? <p>Carregando…</p> : saved.length === 0 ? (
            <p>Nenhum endereço cadastrado neste navegador.</p>
          ) : (
            <>
              <ul className="address-saved">
                {saved.map((item) => (
                  <li key={item.id} className={`address-saved__item${item.id === current?.id ? " address-saved__item--new" : ""}`}>
                    <div className="address-saved__head">
                      <div>
                        <strong>{item.street}, {item.number}{item.complement ? ` · ${item.complement}` : ""}</strong>
                        <span>{item.neighborhood} · {item.city} – {item.state} · CEP {item.postal_code}</span>
                        <small>Comprovante {item.issuer} · confirmado em {new Date(item.confirmed_at).toLocaleString("pt-BR")}</small>
                      </div>
                      <button type="button" className="address-delete" onClick={() => remove(item)}
                        aria-label={`Excluir ${item.street}, ${item.number}`}>Excluir</button>
                    </div>
                    <NearbyList stops={item.nearby_stops} />
                  </li>
                ))}
              </ul>
              <button type="button" className="address-delete" onClick={removeAll}>Excluir todos os meus dados</button>
            </>
          )}
        </section>
      </section>
    </main>
  );
}

function formatAddress(a: Address): string {
  return `${a.street}, ${a.number}${a.complement ? ` · ${a.complement}` : ""} — ${a.neighborhood} · ${a.city} – ${a.state} · CEP ${a.postal_code}`;
}

function NearbyList({ stops }: { stops: NearbyStop[] }) {
  if (!stops.length) {
    return <p className="address-nearby-empty">Ainda não há ponto monitorado pelo UrbanFlow nesta via. Seu endereço ajuda a priorizar os próximos abrigos inteligentes.</p>;
  }
  return (
    <ul className="address-stops" aria-label="Pontos UrbanFlow nesta via">
      {stops.map((stop) => (
        <li key={stop.id} className={`address-stop address-stop--${stop.status}`}>
          <strong>{stop.name}</strong>
          <span>Linha {stop.line} · {stop.count} pessoas · espera ≈ {stop.wait_min} min</span>
          <small>{STATUS_LABEL[stop.status] ?? stop.status}{stop.enroute ? " · ônibus extra a caminho" : ""}</small>
        </li>
      ))}
    </ul>
  );
}
