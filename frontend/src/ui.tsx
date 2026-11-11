import { ReactNode, useCallback, useEffect, useState } from "react";
import { api, Page } from "./api";

export const LABEL: Record<string, string> = {
  disponivel: "Disponível", reservado: "Reservado", em_transito: "Em trânsito", entregue: "Entregue",
  pendente: "Pendente", cancelada: "Cancelada", colhido: "Colhido",
};
export const Badge = ({ s }: { s: string }) => <span className={`badge ${s}`}>{LABEL[s] ?? s}</span>;
export const fmt = (d: string) => new Date(d).toLocaleString("pt-PT", { dateStyle: "short", timeStyle: "short" });

export function useAction() {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const run = async (fn: () => Promise<unknown>) => {
    setError(""); setBusy(true);
    try { await fn(); return true; } catch (e: any) { setError(e.message); return false; } finally { setBusy(false); }
  };
  return { error, busy, run, setError };
}

export const Err = ({ msg }: { msg: string }) => (msg ? <p className="error">{msg}</p> : null);
export const Card = ({ title, children }: { title?: string; children: ReactNode }) => (
  <section className="card">{title && <h3>{title}</h3>}{children}</section>
);
export const Field = ({ label, children }: { label: string; children: ReactNode }) => (
  <label className="field"><span>{label}</span>{children}</label>
);

export function usePaged<T>(path: string, params: Record<string, string>, pageSize = 10) {
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<Page<T>>({ items: [], total: 0 });
  const [error, setError] = useState("");
  const qs = new URLSearchParams({ ...params, limit: String(pageSize), offset: String(offset) }).toString();
  const load = useCallback(
    () => api<Page<T>>(`${path}?${qs}`).then(setData).catch((e) => setError(e.message)), [path, qs]);
  useEffect(() => { load(); }, [load]);
  return { ...data, offset, setOffset, load, pageSize, error };
}

export function SearchBar({ onSearch, placeholder }: { onSearch: (q: string) => void; placeholder: string }) {
  const [v, setV] = useState("");
  return (
    <form className="form" style={{ marginBottom: ".8rem" }} onSubmit={(e) => { e.preventDefault(); onSearch(v.trim()); }}>
      <Field label="Pesquisar"><input placeholder={placeholder} value={v} onChange={(e) => setV(e.target.value)} /></Field>
      <button className="sm" type="submit">Pesquisar</button>
    </form>
  );
}

export function Pager({ offset, pageSize, total, onChange }: {
  offset: number; pageSize: number; total: number; onChange: (o: number) => void;
}) {
  if (total === 0) return <p className="muted">Sem resultados.</p>;
  return (
    <div className="pager">
      <span className="muted">{offset + 1}–{Math.min(offset + pageSize, total)} de {total}</span>
      <button className="sm" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - pageSize))}>← Anterior</button>
      <button className="sm" disabled={offset + pageSize >= total} onClick={() => onChange(offset + pageSize)}>Seguinte →</button>
    </div>
  );
}
