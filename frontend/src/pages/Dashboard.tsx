import { useEffect, useState } from "react";
import { api, Stats } from "../api";
import { Badge, Card, Err } from "../ui";

export default function Dashboard() {
  const [s, setS] = useState<Stats | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api<Stats>("/stats").then(setS).catch((e) => setErr(e.message)); }, []);
  const items: [string, number | undefined][] = [
    ["Produtores", s?.producers], ["Lotes registados", s?.lots], ["Lotes disponíveis", s?.lots_available],
    ["Entregas activas", s?.deliveries_active], ["Entregas concluídas", s?.deliveries_done],
    ["Total registado (kg)", s?.total_kg],
  ];
  const max = Math.max(1, ...(s?.by_product.map((p) => p.kg) ?? [1]));
  return (<><h2>Painel</h2><Err msg={err} />
    <div className="grid">{items.map(([l, v]) => <div className="stat" key={l}><b>{v ?? "–"}</b><span>{l}</span></div>)}</div>
    <div style={{ height: "1rem" }} />
    <Card title="Volume por produto (kg)">
      {s?.by_product.length ? <div className="bars">{s.by_product.map((p) => (
        <div className="bar" key={p.name}><span>{p.name}</span><div style={{ width: `${(p.kg / max) * 100}%` }} /><span>{p.kg}</span></div>))}</div>
        : <p className="muted">Ainda sem lotes.</p>}
    </Card>
    <Card title="Entregas por estado">
      {s?.by_status.length ? s.by_status.map((x) => <p key={x.status}><Badge s={x.status} /> {x.count}</p>)
        : <p className="muted">Ainda sem entregas.</p>}
    </Card></>);
}
