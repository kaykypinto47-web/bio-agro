import { useEffect, useState } from "react";
import { api, Lot, Page, Producer, Product, User } from "../api";
import { Badge, Card, Err, Field, Pager, SearchBar, useAction, usePaged } from "../ui";

const EMPTY = { producer_id: "", product_id: "", quantity: "", harvest_date: "", origin: "" };

export default function Lots({ user }: { user: User }) {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const pg = usePaged<Lot>("/lots", { q, status });
  const [producers, setProducers] = useState<Producer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [f, setF] = useState(EMPTY);
  const [editing, setEditing] = useState<number | null>(null);
  const [qr, setQr] = useState<Lot | null>(null);
  const [newProduct, setNewProduct] = useState("");
  const { error, busy, run } = useAction();
  const canWrite = user.role !== "motorista";

  const loadRefs = () => Promise.all([
    api<Page<Producer>>("/producers?limit=200").then((r) => setProducers(r.items)),
    api<Product[]>("/products").then(setProducts),
  ]);
  useEffect(() => { loadRefs(); }, []);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    run(async () => {
      const body = { producer_id: Number(f.producer_id), product_id: Number(f.product_id),
        quantity: Number(f.quantity), harvest_date: f.harvest_date, origin: f.origin || null };
      editing ? await api(`/lots/${editing}`, "PUT", body) : await api("/lots", "POST", body);
      setF(EMPTY); setEditing(null); await pg.load();
    });
  };
  const edit = (l: Lot) => {
    setEditing(l.id);
    setF({ producer_id: String(l.producer.id), product_id: String(l.product.id), quantity: String(l.quantity),
      harvest_date: l.harvest_date, origin: l.origin ?? "" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const remove = (l: Lot) => {
    if (!confirm(`Eliminar o lote ${l.code}?`)) return;
    run(async () => { await api(`/lots/${l.id}`, "DELETE"); await pg.load(); });
  };
  const addProduct = () => run(async () => { await api("/products", "POST", { name: newProduct }); setNewProduct(""); await loadRefs(); });
  const sel = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  return (<>
    <h2>Lotes</h2>
    {canWrite && <Card title={editing ? "Editar lote" : "Registar lote"}>
      <form className="form" onSubmit={submit}>
        <Field label="Produtor *"><select required value={f.producer_id} onChange={sel("producer_id")}>
          <option value="">—</option>{producers.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></Field>
        <Field label="Produto *"><select required value={f.product_id} onChange={sel("product_id")}>
          <option value="">—</option>{products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></Field>
        <Field label="Quantidade (kg) *"><input required type="number" min="0.01" step="0.01" value={f.quantity} onChange={sel("quantity")} /></Field>
        <Field label="Data de colheita *"><input required type="date" max={new Date().toISOString().slice(0, 10)} value={f.harvest_date} onChange={sel("harvest_date")} /></Field>
        <Field label="Origem"><input value={f.origin} onChange={sel("origin")} /></Field>
        <button className="primary" disabled={busy}>{editing ? "Guardar alterações" : "Registar"}</button>
        {editing && <button className="sm" type="button" onClick={() => { setEditing(null); setF(EMPTY); }}>Cancelar</button>}
      </form>
      {!editing && <div className="form" style={{ marginTop: ".8rem" }}>
        <Field label="Novo produto no catálogo"><input value={newProduct} onChange={(e) => setNewProduct(e.target.value)} /></Field>
        <button className="sm" type="button" disabled={!newProduct || busy} onClick={addProduct}>Adicionar produto</button>
      </div>}
      <Err msg={error} />
    </Card>}

    {qr && <Card title={`Etiqueta · ${qr.code}`}>
      <div className="qr print-area">
        <img src={`/api/lots/${qr.code}/qr.svg`} alt={`QR ${qr.code}`} />
        <p><b>{qr.product.name}</b> · {qr.quantity}kg<br />{qr.code}<br /><small>{qr.producer.name}</small></p>
      </div>
      <button className="primary no-print" onClick={() => window.print()}>Imprimir etiqueta</button>{" "}
      <button className="sm no-print" onClick={() => setQr(null)}>Fechar</button>
    </Card>}

    <Card>
      <SearchBar placeholder="código, produto ou produtor" onSearch={(v) => { setQ(v); pg.setOffset(0); }} />
      <div className="form" style={{ marginBottom: ".6rem" }}>
        <Field label="Estado"><select value={status} onChange={(e) => { setStatus(e.target.value); pg.setOffset(0); }}>
          <option value="">Todos</option><option value="disponivel">Disponível</option><option value="reservado">Reservado</option>
          <option value="em_transito">Em trânsito</option><option value="entregue">Entregue</option></select></Field>
      </div>
      <Err msg={pg.error} />
      <div className="table-wrap"><table>
        <thead><tr><th>Código</th><th>Produto</th><th>Qtd (kg)</th><th>Produtor</th><th>Colheita</th><th>Estado</th><th></th></tr></thead>
        <tbody>{pg.items.map((l) => <tr key={l.id}>
          <td><a href={`#/rastreio?c=${l.code}`}>{l.code}</a></td><td>{l.product.name}</td><td>{l.quantity}</td>
          <td>{l.producer.name}</td><td>{l.harvest_date}</td><td><Badge s={l.status} /></td>
          <td><button className="sm" onClick={() => setQr(l)}>QR</button>
            {canWrite && l.status === "disponivel" && <>
              <button className="sm" onClick={() => edit(l)}>Editar</button>
              <button className="sm danger" onClick={() => remove(l)}>Eliminar</button></>}</td></tr>)}</tbody>
      </table></div>
      <Pager offset={pg.offset} pageSize={pg.pageSize} total={pg.total} onChange={pg.setOffset} />
    </Card></>);
}
