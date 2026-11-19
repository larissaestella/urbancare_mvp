import { reportUrl, type Tipo } from "./Relatorio";

export async function downloadReportPdf(tipo: Tipo, titulo: string, dest: string) {
  const { default: html2pdf } = await import("html2pdf.js");
  const iframe = document.createElement("iframe");
  iframe.setAttribute("aria-hidden", "true");
  iframe.tabIndex = -1;
  iframe.style.cssText = "position:fixed;left:-10000px;top:0;width:1200px;height:900px;border:0";
  const loaded = new Promise<void>((resolve, reject) => {
    const timeout = window.setTimeout(() => reject(new Error("O relatório demorou para carregar.")), 15000);
      iframe.onload = () => {
        window.clearTimeout(timeout);
        resolve();
      };
      iframe.onerror = () => {
        window.clearTimeout(timeout);
        reject(new Error("Não foi possível carregar o relatório."));
      };
  });
  iframe.src = reportUrl(tipo, titulo, dest, false);
  document.body.appendChild(iframe);

  try {
    await loaded;

    let report: HTMLElement | null = null;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      report = iframe.contentDocument?.querySelector<HTMLElement>(".rp-sheet") ?? null;
      if (report) break;
      await new Promise((resolve) => window.setTimeout(resolve, 100));
    }
    if (!report || !iframe.contentDocument) {
      throw new Error("O conteúdo do relatório não foi encontrado.");
    }

    await iframe.contentDocument.fonts.ready;
    const filename = `${titulo}`
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-zA-Z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .toLowerCase();

    await html2pdf()
      .set({
        filename: `${filename || "relatorio"}.pdf`,
        margin: 10,
        image: { type: "jpeg", quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, windowWidth: 1200 },
        jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
      })
      .from(report)
      .save();
  } finally {
    iframe.remove();
  }
}
