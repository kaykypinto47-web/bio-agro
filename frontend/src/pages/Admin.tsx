import { useEffect, useState } from "react";
import { api, User } from "../api";
import { Card, Err, Field, fmt, useAction } from "../ui";

type Log = { id: number; user_id: number | null; action: string; entity: string; entity_id: number | null; detail?: string; created_at: string };
type Verify = { valid: boolean; checked: number; broken_at: number | null };

export default function Admin({ me }: { me: User }) {
  const [users, setUsers] = useState<User[]>([]);
  const [logs, setLogs] = useState<Log[]>([]);
  const [ver, setVer] = useState<Verify | null>(null);
  const [f, setF] = useState({ name: "", email: "", password: "", role: "operador" });
  const { error, busy, run } = useAction();
  const load = async () => { setUsers(await api<User[]>("/users")); setLogs(await api<Log[]>("/audit?limit=50")); };
  useEffect(() => { load(); }, []);
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    run(async () => { await api("/users", "POST", f); setF({ name: "", email: "", password: "", role: "operador" }); await load(); });
  };
  const patch = (u: User, body: object) => run(async () => { await api(`/users/${u.id}`, "PATCH", body); await load(); });
  const resetPw = (u: User) => {
    const pw = prompt(`Nova palavra-passe para ${u.name} (mín. 8 caracteres):`);
    if (pw) patch(u, { password: pw });
  };
  return (<>
    <h2>Administração</h2>
    <Card title="Novo utilizador">
      <form className="form" onSubmit={submit}>
        <Field label="Nome"><input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field label="Email"><input required type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
        <Field label="Palavra-passe (mín. 8)"><input required type="password" minLength={8} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
        <Field label="Perfil"><select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>
          <option value="operador">Operador</option><option value="motorista">Motorista</option><option value="admin">Administrador</option></select></Field>
        <button className="primary" disabled={busy}>Criar</button>
      </form><Err msg={error} />
    </Card>
    <Card title="Utilizadores"><div className="table-wrap"><table>
      <thead><tr><th>Nome</th><th>Email</th><th>Perfil</th><th>Estado</th><th></th></tr></thead>
      <tbody>{users.map((u) => <tr key={u.id}><td>{u.name}</td><td>{u.email}</td>
        <td><select value={u.role} disabled={u.id === me.id} onChange={(e) => patch(u, { role: e.target.value })}>
          <option value="operador">operador</option><option value="motorista">motorista</option><option value="admin">admin</option></select></td>
        <td>{u.active ? "Activo" : "Inactivo"}</td>
        <td><button className="sm" disabled={u.id === me.id} onClick={() => patch(u, { active: !u.active })}>{u.active ? "Desactivar" : "Activar"}</button>
          <button className="sm" onClick={() => resetPw(u)}>Repor palavra-passe</button></td></tr>)}</tbody>
    </table></div></Card>
    <Card title="Auditoria (últimos 50)">
      <button className="sm" onClick={() => run(async () => setVer(await api<Verify>("/audit/verify")))}>Verificar integridade da cadeia</button>
      {ver && <p className={ver.valid ? "ok" : "error"}>{ver.valid
        ? `✔ Cadeia íntegra (${ver.checked} registos verificados).`
        : `✖ Adulteração detectada no registo #${ver.broken_at}.`}</p>}
      <div className="table-wrap"><table>
        <thead><tr><th>Quando</th><th>Utilizador</th><th>Acção</th><th>Entidade</th><th>Detalhe</th></tr></thead>
        <tbody>{logs.map((l) => <tr key={l.id}><td>{fmt(l.created_at)}</td><td>{l.user_id ?? "–"}</td><td>{l.action}</td><td>{l.entity} #{l.entity_id}</td><td>{l.detail}</td></tr>)}</tbody>
      </table></div></Card></>);
}
