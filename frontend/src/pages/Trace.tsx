import { useEffect, useState } from "react";
import { api, Trace } from "../api";
import { Badge, Card, Err, Field, fmt, useAction } from "../ui";

export default function TracePage() {
  const fromHash = new URLSearchParams(location.hash.split("?")[1] ?? "").get("c") ?? "";
  const [code, setCode] = useState(fromHash);
  const [t, setT] = useState<Trace | null>(null);
  const { error, busy, run } = useAction();
  const search = (c = code) => run(async () => { setT(null); setT(await api<Trace>(`/trace/${encodeURIComponent(c.trim())}`)); });
  useEffect(() => { if (fromHash) search(fromHash); }, []);
  return (<>
    <h2>Rastreio de lote</h2>
    <Card>
      <form className="form" onSubmit={(e) => { e.preventDefault(); search(); }}>
        <Field label="Código do lote"><input placeholder="LT-20260101-AB12" value={code} onChange={(e) => setCode(e.target.value)} /></Field>
        <button className="primary" disabled={busy || !code.trim()}>Rastrear</button>
      </form><Err msg={error} />
    </Card>
    {t && <Card title={`${t.product} · ${t.quantity}${t.unit}`}>
      <p>Lote <b>{t.code}</b> <Badge s={t.status} /></p>
      <p className="muted">Produtor: {t.producer.name} ({[t.producer.district, t.producer.province].filter(Boolean).join(", ")})
        · Colheita: {t.harvest_date}{t.origin && ` · Origem: ${t.origin}`}</p>
      <ul className="timeline">{t.timeline.map((e, i) => <li key={i}><b>{e.status}</b> · {fmt(e.at)}{e.note && <div className="muted">{e.note}</div>}</li>)}</ul>
    </Card>}
  </>);
}
