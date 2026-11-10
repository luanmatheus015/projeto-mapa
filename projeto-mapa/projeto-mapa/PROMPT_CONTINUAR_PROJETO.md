# Prompt para continuar o projeto "Mapa de Computadores" em outra IA

> Como usar: cole o bloco **PROMPT** abaixo na nova IA e anexe os arquivos do projeto (`app.py`, `static/index.html`, `static/login.html`, `adduser.py`, `README.md`). Depois descreva o que quer mudar.

---

## PROMPT (copie daqui)

Você vai continuar o desenvolvimento de um sistema web chamado **Mapa de Computadores**. Responda sempre em **português do Brasil**, de forma clara e para uma pessoa que está aprendendo (explique cada comando de terminal). Os arquivos do projeto estão anexados: leia todos antes de responder.

### Objetivo do sistema
O **setor de TI** de uma empresa registra e consulta **todos os computadores e dispositivos de rede**, **andar por andar (Térreo ao 7º andar) e sala por sala**. Serve para saber onde cada máquina está, quem a usa, como acessá-la remotamente (AnyDesk), seu status, ocorrências e histórico de alterações. Só pessoas autorizadas acessam.

### Ambiente e implantação (já em produção)
- Ubuntu Server em uma máquina virtual (rede em modo bridge) no computador pessoal do usuário, IP fixo `192.168.0.186`.
- Código em `/opt/mapa`, serviço systemd `mapa` (usuário `mapa`), servidor `gunicorn` na porta `8080`, banco SQLite em `/opt/mapa/data/mapa.db`.
- Acesso de fora pelo **Tailscale** (sem abrir portas no roteador). Firewall `ufw` liberando SSH, a rede local e a interface `tailscale0` na porta 8080.
- O usuário é iniciante: dê passos curtos e confirmáveis, e sempre informe como **atualizar o servidor** (copiar os arquivos alterados e rodar `sudo systemctl restart mapa`). Os dados do banco não podem ser perdidos em atualizações.

### Tecnologia
- **Backend:** Python 3 + Flask + SQLite (`app.py`). Dependências: `flask`, `gunicorn`.
- **Frontend:** UM único arquivo `static/index.html` com HTML, CSS e JavaScript puro (sem frameworks, sem bibliotecas externas, sem CDN). Mais `static/login.html`.
- Usuários e senhas na tabela `users` (hash do werkzeug). `adduser.py` cria usuários.

### Arquitetura e modelo de dados
- O frontend mantém o estado `S` em memória e faz `PUT /api/state` (com atraso de 400 ms) com o **mapa inteiro** em JSON a cada alteração. `GET /api/state` carrega.
- Estado: `{ "floors": [ [Sala,...] x 8 ] }` (índice 0 = Térreo, 1..7 = 1º..7º andar).
- `Sala = { id, name, pcs: [Dispositivo] }`
- `Dispositivo = { id, worker (nome/trabalhador), tag (código; exibido como "Endereço IP" na ficha), type, status, setor (rótulo "Setor/Sala"), users:[texto], cfg:{host, ip, anydesk, mac, modelo, serie, so, fw, vlan, notas, obs}, extra:[{k,v}], occ:[{id, ts, by, problema, solucao, situacao}] }`
- Tipos: Computador, Notebook, Roteador, Switch, Access Point, Impressora, Servidor, Outro. Status: Ativo, Em manutenção, Em estoque, Desativado.
- **Histórico:** no `PUT /api/state` o servidor compara o estado antigo com o novo (`diff()`) e grava na tabela `history` (quem, quando, andar, sala, dispositivo, campo, antes, depois, ação). Alterações repetidas no mesmo campo, pelo mesmo usuário, em até 300 s são fundidas num registro. Mais de 300 mudanças de uma vez viram um registro "alteração em massa".
- Rotas: `GET /` (exige login), `GET /login.html`, `POST /api/login`, `POST /api/logout`, `GET /api/me`, `GET|PUT /api/state`, `GET /api/history?device=ID&limit=N`. Login com limite de 5 tentativas por IP (bloqueio de 5 min), cookie de sessão HttpOnly/SameSite=Strict.

### Telas e comportamento (no `index.html`)
- **Cabeçalho:** título, botões "Histórico" e "Sair", busca completa (nome, IP, ID Anydesk, modelo, nº de série, usuário, sala, status, texto das ocorrências; sem acento), exportar/importar JSON e "Limpar tudo". Duas abas: **Painel** (tela inicial) e **Mapa dos andares**.
- **Painel:** números (dispositivos, salas, em manutenção, ocorrências abertas, IPs duplicados); campo **Avisos** destacado (IP duplicado, ocorrências abertas, em manutenção; itens clicáveis); status dos equipamentos; últimas alterações; gráficos por andar (clicável) e por tipo; botão **Acessar Zabbix** (`http://10.78.4.7/zabbix/zabbix.php?action=dashboard.view&dashboardid=1`, em nova aba).
- **Mapa:** abas de andar; salas em quadrados com ícones SVG dos dispositivos; clicar abre a **tela da sala** em tela cheia (`#ov`).
- **Tela da sala:** dispositivos em grade de ícones SVG (nome embaixo; tipo, código e status), em dois grupos (computadores/notebooks e rede/outros). Barra com **menu de tipo**, **pesquisa só dentro da sala** (nome, código, host, ID Anydesk, usuários) e **+ Adicionar**. Cada item tem Editar e Remover. Clicar no ícone abre a **ficha**.
- **Ficha (`#dv`, somente leitura):** identificação, usuários, configurações preenchidas, ocorrências e histórico do aparelho; botão **Acessar Remotamente** ao lado do ID Anydesk (link `anydesk:ID`, AnyDesk padrão, ID validado por regex); botão **Editar informações**.
- **Cadastro/edição (mesma tela, `#dv` em modo edição):** campos de identificação, status, setor/sala, usuários, configurações (inclui Notas e Observações), configurações adicionais, ocorrências e o botão **Aplicar Preferências Anteriores** (copia Notas e Observações do último dispositivo da mesma sala e, se preenchido, do mesmo setor/sala). **+ Adicionar** cria um *rascunho* (`draft`) que só entra na sala em **Salvar dispositivo**; **Cancelar** descarta. Edição salva automaticamente a cada digitação.
- **Alerta de IP duplicado:** considera `tag` e `cfg.ip` no formato IPv4; aparece no Painel, no mapa, na ficha e no cadastro (inclusive para rascunho).
- **Visual:** paleta "vermelho acinzentado" (acento `#A94F4F`, degradês em vermelho suave, cinzas claros), modo claro e escuro automáticos por variáveis CSS (`--bg`, `--card`, `--acc`, `--grad`...). Ícones em SVG próprios.

### Decisões já tomadas (respeite)
- Interface toda em português; o rótulo "Setor" é sempre **"Setor/Sala"**.
- Senhas de computadores **não** são guardadas no sistema; só o ID do AnyDesk.
- A edição fica separada da visualização: a ficha é somente leitura, com um botão para editar.
- **Foi removido, por decisão do usuário,** o monitoramento do player de TV e rádio do Portal Cultura. Não reintroduzir sem pedido.
- Não usar `localStorage` para os dados; a fonte da verdade é o servidor.

### Limitações conhecidas (candidatas a melhoria)
- Grava o mapa inteiro a cada alteração: duas pessoas editando juntas, vale a última gravação.
- Sem perfis de acesso (todo usuário logado edita e apaga).
- Exclusão de dispositivo é imediata, sem confirmação.
- Sem testes automatizados.

### Ideias de próximos passos (o usuário já ouviu estas sugestões)
Importar planilha Excel/CSV; perfis de acesso (administrador, analista, só leitura); dados de compra e garantia com aviso de vencimento; relatórios em Excel/PDF; etiqueta com QR code; planta baixa real das salas; HTTPS pelo Tailscale; backup automático para fora da VM; gravação por registro em vez do mapa inteiro.

### Regras de trabalho
1. Antes de alterar, leia os arquivos e diga o que pretende mudar.
2. Entregue **arquivos completos** ou alterações com o trecho exato a substituir; nunca trechos soltos ambíguos.
3. Mantenha compatibilidade com os dados existentes (campos novos devem ter valor padrão; não quebrar o JSON atual).
4. Nunca coloque senhas, `secret.key` ou o banco no código nem no GitHub. A pasta `data/` fica fora do repositório.
5. Teste a sintaxe do que escrever (`python3 -m py_compile` e `node --check`) e explique como o usuário testa no navegador.
6. Ao final, diga os comandos para atualizar o servidor e como reverter.
7. Se algo for ambíguo, faça **uma** pergunta curta antes de construir.

## FIM DO PROMPT
