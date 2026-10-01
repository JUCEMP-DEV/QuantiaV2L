# Frontend local de Quantia V2

Vite se ejecuta en `http://127.0.0.1:5173` y consume FastAPI en `http://127.0.0.1:8000`. No existe configuración de Vercel ni referencia a Render en esta variante.

`Frontend/.env.local` define `VITE_BACKEND_URL`, `VITE_SUPABASE_URL` y la clave pública `VITE_SUPABASE_ANON_KEY`. El archivo se genera con `../scripts/configure-local.ps1` y está ignorado por Git.

Comandos directos:

```powershell
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1
npm.cmd run test:documents
npm.cmd run test:documents:view
```
