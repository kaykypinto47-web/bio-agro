import { useEffect, useState } from "react";
import { api, Delivery, Lot, Page, User } from "../api";
import { Badge, Card, Err, Field, Pager, SearchBar, fmt, useAction, usePaged } from "../ui";

export default function Deliveries({ user }: { user: User }) {
  const [q, setQ] = useState("");
  const [status0, setStatus0] = useState("");
  const pg = usePaged<Delivery>("/deliveries", { q, status: status0 }, 8);
  const [lots, setLots] = useState<Lot[]>([]);
  const [drivers, setDrivers] = useState<User[]>([]);
  const [f, setF] = useState({ lot_id: "", destination: "", driver_id: "" });
  const [created, setCreated] = useState<{ code: string; conf: string } | null>(null);
  const [conf, setConf] = useState<Record<number, { code: string; name: string }>>({});
  const { error, busy, run } = useAction();
  const isDriver = user.role === "motorista";

  const load = async () => {
    await pg.load();
    if (!isDriver) {
      setLots((await api<Page<Lot>>("/lots?status=disponivel&limit=200")).items);
      setDrivers((await api<User[]>("/users")).filter((u) => u.role === "motorista" && u.active !== false));
    }
  };
  useEffect(() => { if (!isDriver) load(); }, []);

  const create = (e: React.FormEvent) => {
    e.preventDefault();
    run(async () => {
      const d = await api<Delivery & { confirmation_code: string }>("/deliveries", "POST", {
        lot_id: Number(f.lot_id), destination: f.destination, driver_id: f.driver_id ? Number(f.driver_id) : null,
      });
      setCreated({ code: d.code, conf: d.confirmation_code });
      setF({ lot_id: "", destination: "", driver_id: "" });
      await load();
    });
  };
  const status = (id: number, s: "em_transito" | "cancelada") =>
    run(async () => { await api(`/deliveries/${id}/status`, "POST", { status: s }); await load(); });
  const confirm = (id: number) => run(async () => {
    const c = conf[id];
    await api(`/deliveries/${id}/confirm`, "POST", { code: c?.code ?? "", receiver_name: c?.name ?? "" });
    await load();
  });
  const setC = (id: number, k: "code" | "name", v: string) =>
    setConf({ ...conf, [id]: { ...(conf[id] ?? { code: "", name: "" }), [k]: v } });

  return (<>
    <h2>Entregas</h2>
    {!isDriver && <Card title="Nova entrega">
      <form className="form" onSubmit={create}>
        <Field label="Lote disponível *"><select required value={f.lot_id} onChange={(e) => setF({ ...f, lot_id: e.target.value })}>
          <option value="">—</option>{lots.map((l) => <option key={l.id} value={l.id}>{l.code} · {l.product.name} · {l.quantity}kg</option>)}</select></Field>
        <Field label="Destino *"><input required minLength={2} value={f.destination} onChange={(e) => setF({ ...f, destination: e.target.value })} /></Field>
        <Field label="Motorista"><select value={f.driver_id} onChange={(e) => setF({ ...f, driver_id: e.target.value })}>
          <option value="">— por atribuir —</option>{drivers.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></Field>
        <button className="primary" disabled={busy}>Criar entrega</button>
      </form>
      {created && <div className="ok">Entrega <b>{created.code}</b> criada. Código de confirmação para o receptor
        (mostrado só uma vez): <div className="code">{created.conf}</div></div>}
      <Err msg={error} />
    </Card>}
    {isDriver && <Err msg={error} />}
    <Card>
      <SearchBar placeholder="código da entrega, destino ou lote" onSearch={(v) => { setQ(v); pg.setOffset(0); }} />
      <div className="form"><Field label="Estado"><select value={status0} onChange={(e) => { setStatus0(e.target.value); pg.setOffset(0); }}>
        <option value="">Todos</option><option value="pendente">Pendente</option><option value="em_transito">Em trânsito</option>
        <option value="entregue">Entregue</option><option value="cancelada">Cancelada</option></select></Field></div>
      <Err msg={pg.error} />
    </Card>
    {pg.items.length === 0 && <Card><p className="muted">Sem entregas.</p></Card>}
    {pg.items.map((d) => (
      <Card key={d.id}>
        <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: ".5rem" }}>
          <div><b>{d.code}</b> · {d.lot.product.name} ({d.lot.quantity}kg) → {d.destination}
            <div className="muted">Lote {d.lot.code} · Motorista: {d.driver?.name ?? "por atribuir"}</div></div>
          <Badge s={d.status} />
        </div>
        <ul className="timeline">{d.events.map((e, i) => <li key={i}><b>{e.status}</b> · {fmt(e.created_at)}{e.note && <div className="muted">{e.note}</div>}</li>)}</ul>
        {d.status === "pendente" && <button className="sm" disabled={busy} onClick={() => status(d.id, "em_transito")}>Iniciar trânsito</button>}
        {!isDriver && ["pendente", "em_transito"].includes(d.status) &&
          <button className="sm" disabled={busy} onClick={() => status(d.id, "cancelada")}>Cancelar</button>}
        {d.status === "em_transito" && (
          <div className="form" style={{ marginTop: ".5rem" }}>
            <Field label="Nome do receptor"><input value={conf[d.id]?.name ?? ""} onChange={(e) => setC(d.id, "name", e.target.value)} /></Field>
            <Field label="Código (6 dígitos)"><input maxLength={6} inputMode="numeric" value={conf[d.id]?.code ?? ""} onChange={(e) => setC(d.id, "code", e.target.value)} /></Field>
            <button className="primary" disabled={busy} onClick={() => confirm(d.id)}>Confirmar entrega</button>
          </div>)}
        {d.status === "entregue" && <p className="muted">Recebido por {d.receiver_name}</p>}
      </Card>))}
    <Pager offset={pg.offset} pageSize={pg.pageSize} total={pg.total} onChange={pg.setOffset} />
  </>);
}
