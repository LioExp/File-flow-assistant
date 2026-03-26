# FileFlow – Organizador Inteligente de Arquivos com Segurança


## 📌 Visão Geral

**FileFlow** nasceu durante **33 dias sem internet**, quando a bagunça digital se tornou insuportável. É uma ferramenta que monitoriza pastas (ex: Downloads, Desktop) e aplica regras de organização automática, deteção de duplicatas e proteção contra deleções acidentais (soft delete). O objetivo é ser um **assistente silencioso** que mantém os teus ficheiros organizados e seguros, sem que precises de pensar nisso.

---

🚀 Funcionalidades (Fase 1):

Monitoramento em tempo real	Observa pastas configuradas e reage a novos arquivos.
Deteção de duplicatas	Calcula hash SHA‑256 para cada arquivo e identifica duplicados (apenas relatório – não apaga automaticamente).
Soft delete	Move arquivos apagados para uma lixeira oculta (~/.fileflow_trash) em vez de eliminar definitivamente. Os arquivos ficam disponíveis por 30 dias.
Organização automática	Move arquivos para subpastas baseadas no tipo (ex: PDF → Documentos, JPG → Imagens) e data de modificação.
Logs coloridos	Exibe no terminal informações detalhadas com níveis INFO, WARNING, ERROR, igual no Nest
Barra de progresso	Durante varreduras iniciais, mostra progresso e tempo estimado.


---

## ⚙️ Como Funciona

1. **Configuração:** o utilizador define pastas a monitorizar (ex: `~/Downloads`) e regras de organização.
2. **Monitor:** o programa corre em background (ou como script agendado) e detecta novos ficheiros.
3. **Processamento:**
   - Calcula o hash do ficheiro.
   - Compara com os já indexados.
   - Se duplicado, gera um relatório.
   - Move para a pasta de destino conforme as regras.
4. **Segurança:** qualquer ficheiro removido pelo utilizador é interceptado e movido para a lixeira oculta do FileFlow (não para a lixeira do sistema).

---

## 🛠️ Tecnologias

- **Python 3.8+**
- `watchdog` – monitoramento de ficheiros
- `hashlib` – cálculo de SHA‑256
- `sqlite3` – armazenamento do índice

---

## 📦 Instalação

```bash
git clone https://github.com/LioExp/fileflow.git
cd fileflow
pip install -r requirements.txt
```

– Um projeto que nasceu no caderno e hoje cuida da minha bagunça digital, não é legal?
