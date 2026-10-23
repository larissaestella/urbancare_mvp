import "@fontsource/barlow/400.css";
import "@fontsource/barlow/500.css";
import "@fontsource/barlow/600.css";
import "@fontsource/barlow-semi-condensed/600.css";
import "@fontsource/barlow-semi-condensed/700.css";
import "./tokens.css";
import { createRoot } from "react-dom/client";
import Primitives from "./Primitives";

createRoot(document.getElementById("root")!).render(
  location.pathname === "/dev/primitives" ? <Primitives /> : <p style={{ padding: 32 }}>UrbanFlow — em construção. <a href="/dev/primitives">/dev/primitives</a></p>,
);
