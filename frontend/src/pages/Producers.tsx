import { useState } from "react";
import { api, Producer, User } from "../api";
import { Card, Err, Field, Pager, SearchBar, useAction, usePaged } from "../ui";

const EMPTY = { name: "", phone: "", province: "", district: "" };

export default function Producers({ user }: { user: User }) {
  const [q, setQ] = useState("");
  const pg = usePaged<Producer>("/producers", { q });
  const [f, setF] = useState(EMPTY);
  const [editing, setEditing] = useState<number | null>(null);
  const { error, busy, run } = useAction();
  const canWrite = user.role !== "motorista";

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    run(async () => {
      const body = { ...f, phone: f.phone || null, district: f.district || null };
      editing ? await api(`/producers/${editing}`, "PUT", body) : await api("/producers", "POST", body);
      setF(EMPTY); setEditing(null); await pg.load();
    });
  };
  const edit = (p: Producer) => {
    setEditing(p.id);
    setF({ name: p.name, phone: p.phone ?? "", province: p.province, district: p.district ?? "" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  return (<>
    <h2>Produtores</h2>
    {canWrite && <Card title={editing ? "Editar produtor" : "Novo produtor"}>
      <form className="form" onSubmit={submit}>
        <Field label="Nome *"><input required value={f.name} onChange={set("name")} /></Field>
        <Field label="Telefone"><input value={f.phone} onChange={set("phone")} /></Field>
        <Field label="Província *"><input required value={f.province} onChange={set("province")} /></Field>
        <Field label="Distrito"><input value={f.district} onChange={set("district")} /></Field>
        <button className="primary" disabled={busy}>{editing ? "Guardar alterações" : "Guardar"}</button>
        {editing && <button className="sm" type="button" onClick={() => { setEditing(null); setF(EMPTY); }}>Cancelar</button>}
      </form><Err msg={error} />
    </Card>}
    <Card>
      <SearchBar placeholder="nome, província ou distrito" onSearch={(v) => { setQ(v); pg.setOffset(0); }} />
      <Err msg={pg.error} />
      <div className="table-wrap"><table>
        <thead><tr><th>Nome</th><th>Telefone</th><th>Província</th><th>Distrito</th>{canWrite && <th></th>}</tr></thead>
        <tbody>{pg.items.map((p) => <tr key={p.id}><td>{p.name}</td><td>{p.phone ?? "–"}</td><td>{p.province}</td>
          <td>{p.district ?? "–"}</td>{canWrite && <td><button className="sm" onClick={() => edit(p)}>Editar</button></td>}</tr>)}</tbody>
      </table></div>
      <Pager offset={pg.offset} pageSize={pg.pageSize} total={pg.total} onChange={pg.setOffset} />
    </Card></>);
}
