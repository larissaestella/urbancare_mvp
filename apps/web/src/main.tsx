import "@fontsource/barlow/400.css";
import "@fontsource/barlow/500.css";
import "@fontsource/barlow/600.css";
import "@fontsource/barlow-semi-condensed/600.css";
import "@fontsource/barlow-semi-condensed/700.css";
import "./tokens.css";
import { createRoot } from "react-dom/client";
import Bastidor from "./Bastidor";
import Configuracoes from "./Configuracoes";
import Conversao from "./Conversao";
import Detail from "./Detail";
import Frota from "./Frota";
import Landing from "./Landing";
import Overview from "./Overview";
import Pontos from "./Pontos";
import Primitives from "./Primitives";
import Publicidade from "./Publicidade";
import Relatorio from "./Relatorio";
import Relatorios from "./Relatorios";

const ROUTES: Record<string, () => JSX.Element> = {
  "/dev/primitives": Primitives, "/bastidor": Bastidor, "/landing": Landing, "/landing/metricas": Conversao,
  "/publicidade": Publicidade, "/frota": Frota, "/relatorios": Relatorios, "/configuracoes": Configuracoes, "/relatorios/ver": Relatorio, "/pontos": Pontos,
};
const Screen = ROUTES[location.pathname] ?? (location.pathname.startsWith("/pontos/") ? Detail : Overview);

createRoot(document.getElementById("root")!).render(<Screen />);
