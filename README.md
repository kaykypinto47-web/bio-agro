# BIO-AGRO

Sistema de rastreabilidade e gestão de entregas de apoio agrícola.

## O que já funciona (v0.3)
- **Autenticação** JWT com perfis `admin`, `operador` e `motorista` (permissões aplicadas no backend), mudança de palavra-passe e **bloqueio após 5 logins falhados** (15 min).
- **Produtores, produtos e lotes** com **criar, editar e eliminar** (lotes só enquanto disponíveis), **pesquisa, filtros e paginação**.
- **QR Code por lote** (`/api/lots/{codigo}/qr.svg`) com etiqueta imprimível; aponta para o rastreio público.
- **Entregas** `pendente → em_transito → entregue` (ou `cancelada`), linha do tempo, e **confirmação por código de 6 dígitos** (só o hash é guardado; alternativa à biometria).
- **Rastreio público** de lote por código, sem expor dados sensíveis.
- **Auditoria com cadeia de hashes**: cada registo inclui o hash do anterior e o admin pode **verificar a integridade** (detecta registos alterados ou removidos do meio da cadeia).
- **Gestão de utilizadores** (criar, mudar perfil, activar/desactivar, repor palavra-passe) e **painel com gráficos**.
- **Docker completo** (db + API + frontend) e **12 testes** automáticos do backend.
- Biometria: módulo isolado em `backend/app/biometrics.py` (por implementar, com consentimento informado).

## Requisitos
Windows 11, VS Code, Python 3.11+, Node.js LTS, Docker Desktop (ou PostgreSQL local).

## Arranque rápido

### Opção A — tudo com Docker (um comando)
```powershell
docker compose up -d --build
```
Abrir http://localhost:8080 (API em :8000). Variáveis opcionais: `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `PUBLIC_URL`.

### Opção B — desenvolvimento (abaixo)

### 1. Base de dados (raiz do projecto)
```powershell
docker compose up -d db
```

### 2. Backend
```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env     # edite SECRET_KEY e ADMIN_PASSWORD
python -m app.seed              # (opcional) dados FICTÍCIOS de demonstração
uvicorn app.main:app --reload
```
API: http://127.0.0.1:8000 · Docs: http://127.0.0.1:8000/docs

Conta admin inicial (criada no 1.º arranque, vem do `.env`): `admin@bioagro.co.mz` / `Admin@12345` — **mude-a**.
Motorista de demonstração (após o seed): `motorista@bioagro.co.mz` / `Motorista@123`.

Testes: `pytest -q` (usam SQLite em memória; não precisam do Docker).

### 3. Frontend (novo terminal)
```powershell
cd frontend
npm install
npm run dev
```
http://localhost:5173 (o Vite faz proxy de `/api` para o backend).

## Fluxo para experimentar
1. Entrar como admin → criar produtor → registar lote.
2. Criar entrega para o lote (atribuir o motorista) → anotar o código de 6 dígitos.
3. Entrar como motorista → "Iniciar trânsito" → "Confirmar entrega" com nome + código.
4. Rastreio: pesquisar o código do lote (funciona também sem login).

## Notas importantes
- As tabelas são criadas com `create_all`. Se vinha de uma versão anterior, a tabela de auditoria ganhou colunas: apague o volume (`docker compose down -v`) ou use Alembic.
- O QR Code usa `PUBLIC_URL`; para imprimir etiquetas que funcionem fora do seu PC, defina-o com o endereço real do sistema.
- O limite de login é em memória (1 processo). Com vários servidores, usar Redis.
- A cadeia de hashes detecta alterações, mas quem controla a base de dados pode apagar o fim da cadeia; para mais garantias, guardar periodicamente o último hash noutro local.

## Próximas etapas
Alembic, SMS/WhatsApp (código ao receptor), pagamentos M-Pesa/e-Mola, mapa/GPS, PWA offline, biometria com consentimento, assinatura digital dos eventos, HTTPS.

## Princípios
- Usar dados fictícios durante o desenvolvimento.
- Não guardar imagens de assinatura como único dado biométrico.
- Obter consentimento informado antes de recolher amostras biométricas.
- Disponibilizar confirmação alternativa à biometria.
- Não incluir segredos reais no Git; manter `.env` fora do controlo de versões.
