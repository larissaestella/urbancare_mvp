import { useEffect, useRef, useState, type ReactNode } from "react";
import { NAV, go } from "./Overview";
import { Button, Segmented, Sidebar, StatusShape, TitlePlate, Toggle } from "./ui";
import chevron from "./assets/chevron.svg";
import chevronOnInk from "./assets/chevron-on-ink.svg";
import "./overview.css";
import "./configuracoes.css";

/* Configurações (Figma 06, nó 32:112). Texto verbatim do Figma; rótulo de dados segue §8.1.
   Seções colapsáveis (Conta e Aparência abrem abertas, como no Figma). Nada é gravado: a regra de envio da simulação
   continua fixa em > 20 por 5 min (rules.THRESHOLD) para não descalibrar o cenário Demo.
   Trocar foto, Alterar senha e as sessões funcionam só nesta tela (sem login real; PLANO §8.6); Sair e os documentos avisam. */
const AVISO = "Conta e segurança entram com o login real, depois do piloto.";

function Section({ title, summary, open, onToggle, children }:
  { title: string; summary: string; open: boolean; onToggle: () => void; children: ReactNode }) {
  return (
    <section className="cf-sec">
      <button className="cf-sec__head" aria-expanded={open} onClick={onToggle}>
        <span className="t-title cf-sec__title">{title}</span>
        <span className="cf-sec__summary">{summary}</span>
        <img className="cf-sec__chev" src={chevronOnInk} alt="" />
      </button>
      {open && <div className="cf-sec__body">{children}</div>}
    </section>
  );
}

function Row({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="cf-row">
      <div className="cf-row__label"><strong>{label}</strong>{hint && <span>{hint}</span>}</div>
      {children}
    </div>
  );
}

const Field = ({ value, label, readOnly }: { value: string; label: string; readOnly?: boolean }) =>
  <input className="cf-field" defaultValue={value} aria-label={label} readOnly={readOnly} />;

// o Figma só mostra o valor escolhido; sem inventar as demais opções
const Select = ({ value, label }: { value: string; label: string }) => (
  <span className="cf-select">
    <select className="cf-field" aria-label={label} defaultValue={value}><option>{value}</option></select>
    <img src={chevron} alt="" />
  </span>
);

const TEMAS = ["Claro", "Escuro", "Sistema"] as const;
const DENSIDADES = ["Confortável", "Compacta"] as const;
const DIAS = ["Seg", "Dom"] as const;

export default function Configuracoes() {
  const [open, setOpen] = useState({ conta: true, aparencia: true, idioma: false, regra: false, seguranca: false, sobre: false });
  const flip = (k: keyof typeof open) => setOpen((o) => ({ ...o, [k]: !o[k] }));
  const [tema, setTema] = useState<(typeof TEMAS)[number]>("Claro");
  const [densidade, setDensidade] = useState<(typeof DENSIDADES)[number]>("Confortável");
  const [dia, setDia] = useState<(typeof DIAS)[number]>("Seg");
  const [sw, setSw] = useState({ formas: true, ruas: true, animacoes: true, regra: true, duasEtapas: true });
  const toggle = (k: keyof typeof sw, label: string) =>
    <Toggle on={sw[k]} label={label} onChange={(v) => setSw((s) => ({ ...s, [k]: v }))} />;
  const [toast, setToast] = useState<string | null>(null);
  const avisar = () => setToast(AVISO);
  const [foto, setFoto] = useState<string | null>(null);
  const fotoInput = useRef<HTMLInputElement>(null);
  const [dialog, setDialog] = useState<"senha" | "sessoes" | "encerrar" | null>(null);
  const [senhaDias, setSenhaDias] = useState(32);
  const [celular, setCelular] = useState(true);
  const sessoes = celular ? "2 dispositivos · este computador e um celular" : "1 dispositivo · este computador";

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 5000);
    return () => window.clearTimeout(t);
  }, [toast]);

  return (
    <div className="app">
      <Sidebar items={NAV} active="Configurações" onNavigate={go} />
      <main className="ov cf">
        <TitlePlate title="Configurações" meta="Conta, aparência, idioma e região, regra de envio e segurança" />

        <Section title="Conta" summary="Carla Mendes · Concessionária Via Sul" open={open.conta} onToggle={() => flip("conta")}>
          <div className="cf-row cf-profile">
            <span className="cf-avatar">{foto ? <img src={foto} alt="Foto de Carla Mendes" /> : "CM"}</span>
            <div className="cf-profile__name"><strong>Carla Mendes</strong><span>Gestora de operação · Concessionária Via Sul</span></div>
            <input ref={fotoInput} type="file" accept="image/*" hidden aria-label="Escolher foto" onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) { setFoto(URL.createObjectURL(f)); setToast("Foto atualizada."); }
            }} />
            <Button variant="secondary" onClick={() => fotoInput.current?.click()}>Trocar foto</Button>
          </div>
          <Row label="Nome completo"><Field label="Nome completo" value="Carla Mendes" /></Row>
          <Row label="E-mail" hint="Usado para login e para o resumo diário"><Field label="E-mail" value="carla.mendes@viasul.com.br" /></Row>
          <Row label="Cargo"><Select label="Cargo" value="Gestora de operação" /></Row>
          <Row label="Organização" hint="Definida pelo administrador da conta">
            <Field label="Organização" value="Concessionária Via Sul" readOnly />
          </Row>
          <Row label="Senha" hint={senhaDias ? `Alterada há ${senhaDias} dias` : "Alterada agora"}>
            <Button variant="secondary" onClick={() => setDialog("senha")}>Alterar senha</Button>
          </Row>
        </Section>

        <Section title="Aparência" summary={`${tema} · ${densidade}`} open={open.aparencia} onToggle={() => flip("aparencia")}>
          <Row label="Tema" hint="Claro é o padrão para salas de operação iluminadas">
            <Segmented options={[...TEMAS]} value={tema} onChange={setTema} />
          </Row>
          <Row label="Densidade" hint="Espaçamento entre linhas de tabelas e listas">
            <Segmented options={[...DENSIDADES]} value={densidade} onChange={setDensidade} />
          </Row>
          <Row label="Tamanho do texto"><Select label="Tamanho do texto" value="Padrão (14 px)" /></Row>
          <Row label="Mostrar formas nos status" hint="Círculo, triângulo e quadrado além da cor">
            {toggle("formas", "Mostrar formas nos status")}
          </Row>
          <Row label="Rótulos de ruas no mapa">{toggle("ruas", "Rótulos de ruas no mapa")}</Row>
          <Row label="Animações" hint="Transições entre telas e gráficos">{toggle("animacoes", "Animações")}</Row>
        </Section>

        <Section title="Idioma e região" summary="Português (Brasil) · GMT−3" open={open.idioma} onToggle={() => flip("idioma")}>
          <Row label="Idioma"><Select label="Idioma" value="Português (Brasil)" /></Row>
          <Row label="Fuso horário"><Select label="Fuso horário" value="Brasília (GMT−3)" /></Row>
          <Row label="Formato de data"><Select label="Formato de data" value="DD/MM/AAAA" /></Row>
          <Row label="Primeiro dia da semana" hint="Usado no mapa de calor e nos relatórios semanais">
            <Segmented options={[...DIAS]} value={dia} onChange={setDia} />
          </Row>
        </Section>

        <Section title="Regra de envio automático" summary={sw.regra ? "Ativa · > 20 pessoas por 5 min" : "Inativa · > 20 pessoas por 5 min"}
          open={open.regra} onToggle={() => flip("regra")}>
          <Row label="Regra ativa" hint="Alertar a garagem mais próxima e sugerir ônibus extra na linha com maior demanda">
            {toggle("regra", "Regra ativa")}
          </Row>
          <Row label="Limite de lotação"><Field label="Limite de lotação" value="20 pessoas" readOnly /></Row>
          <Row label="Tempo acima do limite"><Field label="Tempo acima do limite" value="5 min" readOnly /></Row>
          <Row label="Garagem acionada"><Select label="Garagem acionada" value="Mais próxima do ponto" /></Row>
          <Row label="Linha priorizada"><Select label="Linha priorizada" value="Maior demanda" /></Row>
        </Section>

        <Section title="Segurança" summary="Verificação em duas etapas ativa" open={open.seguranca} onToggle={() => flip("seguranca")}>
          <Row label="Verificação em duas etapas" hint="Código por aplicativo autenticador">
            {toggle("duasEtapas", "Verificação em duas etapas")}
          </Row>
          <Row label="Sessões ativas" hint={sessoes}>
            <Button variant="secondary" onClick={() => setDialog("sessoes")}>Ver sessões</Button>
          </Row>
          <Row label="Último acesso"><span className="cf-value">Hoje, 18:40 · São Paulo</span></Row>
        </Section>

        <Section title="Sobre" summary="Protótipo Sprint 2" open={open.sobre} onToggle={() => flip("sobre")}>
          <Row label="Versão"><span className="cf-value">Protótipo Sprint 2 · simulação</span></Row>
          <Row label="Termos de uso"><button className="cf-link" onClick={avisar}>Ler termos →</button></Row>
          <Row label="Política de privacidade"><button className="cf-link" onClick={avisar}>Ler política →</button></Row>
          <Row label="Central de ajuda"><button className="cf-link" onClick={avisar}>Abrir ajuda →</button></Row>
        </Section>

        <section className="cf-exit">
          <div className="cf-row">
            <div className="cf-exit__label"><strong>Sair da conta</strong><span>Você será desconectado deste computador.</span></div>
            <Button onClick={avisar}>Sair</Button>
          </div>
          <div className="cf-row">
            <div className="cf-exit__label"><strong>Encerrar todas as sessões</strong><span>Desconecta este computador e o celular vinculado.</span></div>
            <Button variant="secondary" onClick={() => setDialog("encerrar")}>Encerrar sessões</Button>
          </div>
        </section>

        <p className="cf-foot">Dados ilustrativos — simulação para validação (Sprint 2).</p>
      </main>
      {dialog === "senha" && <SenhaDialog onClose={() => setDialog(null)} onDone={() => { setDialog(null); setSenhaDias(0); setToast("Senha alterada."); }} />}
      {dialog === "sessoes" && (
        <Dialog title="Sessões ativas" onClose={() => setDialog(null)}>
          <ul className="cf-sessions">
            <li><div><strong>Este computador</strong><span>Chrome · São Paulo · ativo agora</span></div><span className="cf-sessions__now">Esta sessão</span></li>
            {celular && <li><div><strong>Celular</strong><span>App UrbanFlow · São Paulo · último acesso hoje, 07:12</span></div>
              <Button variant="secondary" onClick={() => { setCelular(false); setToast("Sessão do celular encerrada."); }}>Encerrar</Button></li>}
          </ul>
        </Dialog>
      )}
      {dialog === "encerrar" && (
        <Dialog title="Encerrar todas as sessões" onClose={() => setDialog(null)}>
          <p>Desconecta este computador e o celular vinculado. Você vai precisar entrar de novo nos dois.</p>
          <div className="dialog__actions">
            <Button variant="secondary" onClick={() => setDialog(null)}>Cancelar</Button>
            <Button onClick={() => { setDialog(null); setCelular(false); setToast("Sessões encerradas. No protótipo você continua conectado, porque não há login real."); }}>Encerrar sessões</Button>
          </div>
        </Dialog>
      )}
      {toast && <div className="toast cf-toast" role="status"><StatusShape status="normal" color="var(--info-blue-on-ink)" />{toast}</div>}
    </div>
  );
}

function Dialog({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onClose]);
  return (
    <div className="overlay" onClick={onClose}>
      <div className="dialog cf-dialog" role="dialog" aria-modal="true" aria-labelledby="cf-dlg-title" onClick={(e) => e.stopPropagation()}>
        <header className="dialog__band"><span className="dialog__mark" /><h2 id="cf-dlg-title" className="t-title">{title}</h2>
          <button className="cf-dialog__close" aria-label="Fechar" onClick={onClose}>×</button></header>
        <div className="dialog__body">{children}</div>
      </div>
    </div>
  );
}

function SenhaDialog({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const [atual, setAtual] = useState(""), [nova, setNova] = useState(""), [conf, setConf] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  function salvar(e: React.FormEvent) {
    e.preventDefault();
    if (!atual) return setErro("Informe a senha atual.");
    if (nova.length < 8) return setErro("A nova senha precisa ter pelo menos 8 caracteres.");
    if (nova === atual) return setErro("A nova senha precisa ser diferente da atual.");
    if (nova !== conf) return setErro("A confirmação não confere com a nova senha.");
    onDone();
  }
  return (
    <Dialog title="Alterar senha" onClose={onClose}>
      <form className="cf-form" onSubmit={salvar} noValidate>
        <label>Senha atual<input className="cf-field" type="password" autoComplete="current-password" value={atual} onChange={(e) => setAtual(e.target.value)} autoFocus /></label>
        <label>Nova senha<input className="cf-field" type="password" autoComplete="new-password" value={nova} onChange={(e) => setNova(e.target.value)} /></label>
        <label>Confirmar nova senha<input className="cf-field" type="password" autoComplete="new-password" value={conf} onChange={(e) => setConf(e.target.value)} /></label>
        {erro && <p className="cf-form__err" role="alert">{erro}</p>}
        <div className="dialog__actions">
          <Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button type="submit">Salvar senha</Button>
        </div>
      </form>
    </Dialog>
  );
}
