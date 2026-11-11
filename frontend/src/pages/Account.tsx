import { useState } from "react";
import { api, User } from "../api";
import { Card, Err, Field, useAction } from "../ui";

export default function Account({ user }: { user: User }) {
  const [f, setF] = useState({ current_password: "", new_password: "", confirm: "" });
  const [done, setDone] = useState(false);
  const { error, busy, run, setError } = useAction();
  const submit = (e: React.FormEvent) => {
    e.preventDefault(); setDone(false);
    if (f.new_password !== f.confirm) return setError("A confirmação não coincide com a nova palavra-passe");
    run(async () => {
      await api("/auth/change-password", "POST", { current_password: f.current_password, new_password: f.new_password });
      setF({ current_password: "", new_password: "", confirm: "" }); setDone(true);
    });
  };
  return (<>
    <h2>A minha conta</h2>
    <Card title={`${user.name} · ${user.email}`}>
      <form className="form" onSubmit={submit}>
        <Field label="Palavra-passe actual"><input required type="password" value={f.current_password} onChange={(e) => setF({ ...f, current_password: e.target.value })} /></Field>
        <Field label="Nova (mín. 8)"><input required minLength={8} type="password" value={f.new_password} onChange={(e) => setF({ ...f, new_password: e.target.value })} /></Field>
        <Field label="Confirmar nova"><input required minLength={8} type="password" value={f.confirm} onChange={(e) => setF({ ...f, confirm: e.target.value })} /></Field>
        <button className="primary" disabled={busy}>Alterar palavra-passe</button>
      </form>
      <Err msg={error} />{done && <p className="ok">Palavra-passe alterada.</p>}
    </Card></>);
}
