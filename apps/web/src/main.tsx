import "@fontsource/barlow/400.css";
import "@fontsource/barlow/500.css";
import "@fontsource/barlow/600.css";
import "@fontsource/barlow-semi-condensed/600.css";
import "@fontsource/barlow-semi-condensed/700.css";
import "./tokens.css";
import { createRoot } from "react-dom/client";
import Bastidor from "./Bastidor";
import Conversao from "./Conversao";
import Landing from "./Landing";
import Overview from "./Overview";
import Primitives from "./Primitives";

const ROUTES: Record<string, () => JSX.Element> = {
  "/dev/primitives": Primitives, "/bastidor": Bastidor, "/landing": Landing, "/landing/metricas": Conversao,
};
const Screen = ROUTES[location.pathname] ?? Overview;

createRoot(document.getElementById("root")!).render(<Screen />);
