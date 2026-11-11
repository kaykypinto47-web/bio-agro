import { useEffect, useState } from "react";
import { api, hasToken, setToken, User } from "./api";
import { Card, Err, Field, useAction } from "./ui";
import Dashboard from "./pages/Dashboard";
import Producers from "./pages/Producers";
import Lots from "./pages/Lots";
import Deliveries from "./pages/Deliveries";
import TracePage from "./pages/Trace";
import Admin from "./pages/Admin";
import Account from "./pages/Account";

type Tab = "painel" | "produtores" | "lotes" | "entregas" | "rastreio" | "admin" | "conta";

function Login({ onDone }: { onDone: (u: User) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { error, busy, run } = useAction();
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    run(async () => {
      const r = await api<{ access_token: string; user: User }>("/auth/login", "POST", { email, password });
      setToken(r.access_token);
      onDone(r.user);
    });
  };
  return (
    <div className="login">
      <Card title="BIO-AGRO · Entrar">
        <form onSubmit={submit} className="form" style={{ gridTemplateColumns: "1fr" }}>
          <Field label="Email"><input value={email} onChange={(e) => setEmail(e.target.value)} autoFocus /></Field>
          <Field label="Palavra-passe">
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <button className="primary" disabled={busy}>Entrar</button>
        </form>
        <Err msg={error} />
        <p className="muted">Consulta pública de lotes: <a href="#/rastreio">rastrear um lote</a></p>
      </Card>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(!hasToken());
  const [tab, setTab] = useState<Tab>("painel");
  const [publicTrace, setPublicTrace] = useState(location.hash.startsWith("#/rastreio"));

  useEffect(() => {
    if (hasToken()) api<User>("/auth/me").then(setUser).catch(() => setToken(null)).finally(() => setReady(true));
    const h = () => setPublicTrace(location.hash.startsWith("#/rastreio"));
    window.addEventListener("hashchange", h);
    return () => window.removeEventListener("hashchange", h);
  }, []);

  if (!ready) return null;
  if (!user) {
    return publicTrace ? (
      <main><TracePage /><p><a href="#/">← Entrar no sistema</a></p></main>
    ) : <Login onDone={setUser} />;
  }

  const isDriver = user.role === "motorista";
  const tabs: [Tab, string][] = [
    ["painel", "Painel"],
    ...(isDriver ? [] : ([["produtores", "Produtores"], ["lotes", "Lotes"]] as [Tab, string][])),
    ["entregas", "Entregas"], ["rastreio", "Rastreio"], ["conta", "Conta"],
    ...(user.role === "admin" ? ([["admin", "Administração"]] as [Tab, string][]) : []),
  ];

  return (
    <>
      <header>
        <h1>🌱 BIO-AGRO</h1>
        <nav>{tabs.map(([k, l]) => <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}</nav>
        <span>{user.name} ({user.role})</span>
        <button className="ghost" onClick={() => { setToken(null); setUser(null); }}>Sair</button>
      </header>
      <main>
        {tab === "painel" && <Dashboard />}
        {tab === "produtores" && <Producers user={user} />}
        {tab === "lotes" && <Lots user={user} />}
        {tab === "entregas" && <Deliveries user={user} />}
        {tab === "rastreio" && <TracePage />}
        {tab === "admin" && <Admin me={user} />}
        {tab === "conta" && <Account user={user} />}
      </main>
    </>
  );
}
