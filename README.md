# Mapa de Computadores

Sistema web para o **setor de TI** registrar e consultar todos os computadores e dispositivos de rede de uma empresa, **andar por andar (Térreo ao 7º) e sala por sala**. Roda em um **Ubuntu Server** (uma máquina virtual), guarda os dados em um **banco de dados** no próprio servidor e só abre para **pessoas autorizadas** (login com usuário e senha).

---

## 1. O que o sistema faz

### Painel (tela inicial)
- **Números principais:** dispositivos, salas, em manutenção, ocorrências abertas e IPs duplicados.
- **Avisos:** campo destacado com IPs duplicados, ocorrências abertas e equipamentos em manutenção. Cada item é clicável e abre o dispositivo.
- **Status dos equipamentos:** barra com ativos, em manutenção, em estoque e desativados.
- **Últimas alterações:** as mais recentes do histórico.
- **Gráficos:** dispositivos por andar (clicar abre o andar) e por tipo.
- **Botão "Acessar Zabbix":** abre o painel do Zabbix em outra aba (veja a observação na seção 9).

### Mapa dos andares
- Uma aba por andar (Térreo, 1º ao 7º), com as salas em quadrados que mostram os dispositivos em ícones.
- Clicar em uma sala abre a **tela da sala**, em tela cheia.

### Tela da sala
- Lista os dispositivos em **ícones** (computador, notebook, roteador, switch, access point, impressora, servidor), separados em "Computadores e notebooks" e "Dispositivos de rede e outros".
- Barra de ações: **menu de tipo**, **pesquisa** (usuário, nome do computador/host, nome/trabalhador, código e ID Anydesk, só dentro da sala) e **+ Adicionar**.
- Cada dispositivo tem **Editar** e **Remover**. Clicar no ícone abre a ficha.

### Ficha do dispositivo (somente leitura)
- **Identificação:** nome/trabalhador, endereço IP (código), tipo, status, setor/sala, sala e andar.
- **Usuários**, **Configurações** (só o que estiver preenchido), **Ocorrências** e **Histórico de alterações** do aparelho.
- Ao lado do **ID Anydesk**, o botão **Acessar Remotamente** abre o AnyDesk já conectando ao computador (só falta digitar a senha).
- Botão **Editar informações** no topo.

### Tela de cadastro/edição (a mesma para Adicionar e Editar)
- Nome/trabalhador, código/IP, tipo, **status**, **setor/sala**, usuários, configurações (host, IP, ID Anydesk, MAC, modelo, nº de série, sistema operacional ou firmware/VLAN, **notas**, **observações**), configurações adicionais livres e **ocorrências** (problema, solução, situação).
- **Aplicar Preferências Anteriores:** copia Notas e Observações do último dispositivo cadastrado na mesma sala (e no mesmo setor/sala, se preenchido).
- Em um cadastro novo, o dispositivo só entra na sala ao clicar em **Salvar dispositivo**. **Cancelar** descarta.

### Outras funções
- **Busca completa** (topo): nome, IP, ID Anydesk, modelo, nº de série, usuário, sala, status e texto das ocorrências, sem diferenciar acentos.
- **Histórico de alterações:** quem mudou o quê e quando, no botão "Histórico" e na ficha de cada aparelho. Mudanças repetidas no mesmo campo em até 5 minutos viram um único registro.
- **Alerta de IP duplicado:** no Painel, no mapa e dentro da ficha e do cadastro.
- **Status do equipamento:** Ativo, Em manutenção, Em estoque, Desativado (com bolinha de cor; desativados ficam esmaecidos).
- **Exportar / Importar** os dados em arquivo JSON e **Limpar tudo**.
- **Visual:** paleta vermelho acinzentado com degradês, com modo claro e escuro automáticos.

---

## 2. Como funciona

```
Navegador  ──HTTP──►  gunicorn (porta 8080)  ──►  Flask (app.py)  ──►  SQLite (data/mapa.db)
 (index.html)            systemd: mapa.service        login, sessão,        usuários, estado do mapa
                                                      API e histórico       e histórico
```

- **Frontend:** um único arquivo, `static/index.html` (HTML, CSS e JavaScript puro, sem bibliotecas). Mantém o estado do mapa em memória e grava no servidor, de forma automática, 0,4 s após cada alteração.
- **Backend:** `app.py` (Flask). Autentica, serve as páginas, guarda o estado completo do mapa em uma tabela e calcula o histórico comparando o estado antigo com o novo a cada gravação.
- **Banco:** SQLite, um arquivo só em `data/mapa.db`. Tabelas: `users`, `state` (uma linha com o JSON do mapa) e `history`.

## 3. Estrutura do repositório

```
projeto-mapa/
├── app.py                 # servidor (Flask): login, API, histórico
├── adduser.py             # cria ou troca a senha de um usuário
├── requirements.txt       # dependências Python (flask, gunicorn)
├── mapa.service           # serviço systemd
├── static/
│   ├── index.html         # todo o site (Painel, Mapa, salas, fichas)
│   └── login.html         # tela de login
├── .gitignore             # impede enviar dados e segredos ao GitHub
├── README.md              # este arquivo
└── PROMPT_CONTINUAR_PROJETO.md   # briefing para continuar em outra IA
```
A pasta `data/` (banco e chave secreta) é criada no servidor e **não vai para o GitHub**.

## 4. Instalação no Ubuntu Server

Pré-requisitos: Ubuntu Server com rede em modo *bridge*, IP fixo (reserva no roteador) e acesso SSH.

```bash
# 1) Sistema
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv ufw git sqlite3
sudo adduser --system --group --home /opt/mapa mapa

# 2) Código (opção A: GitHub, repositório público ou com token)
sudo git clone https://github.com/luanmatheus015/projeto-mapa.git /opt/mapa
#    (opção B: envie o .zip do projeto com scp e descompacte em /opt/mapa)

# 3) Ambiente Python
cd /opt/mapa
sudo python3 -m venv venv
sudo venv/bin/pip install -r requirements.txt
sudo chown -R mapa:mapa /opt/mapa && sudo chmod 755 /opt/mapa

# 4) Primeiro usuário (repita para cada pessoa autorizada)
sudo -H -u mapa bash -c 'cd /opt/mapa && venv/bin/python adduser.py'

# 5) Serviço
sudo cp /opt/mapa/mapa.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mapa
sudo systemctl status mapa

# 6) Firewall (troque a faixa pela sua rede)
sudo ufw allow OpenSSH
sudo ufw allow from 192.168.0.0/24 to any port 8080
sudo ufw enable
```
Teste em `http://IP_DO_SERVIDOR:8080`.

## 5. Acesso de qualquer lugar (Tailscale, recomendado)

O Tailscale cria uma rede privada entre os aparelhos, **sem abrir portas no roteador**.
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
sudo ufw allow in on tailscale0 to any port 8080
```
Instale o Tailscale nos aparelhos autorizados, convide as pessoas para a sua rede e acesse por `http://IP_DO_TAILSCALE:8080`. Quem não foi convidado nem enxerga o site, e quem entra ainda precisa de usuário e senha. **Não é recomendado** abrir a porta 8080 diretamente para a internet.

## 6. Operação do dia a dia

| Tarefa | Comando |
|---|---|
| Criar usuário / trocar senha | `sudo -H -u mapa bash -c 'cd /opt/mapa && venv/bin/python adduser.py'` |
| Remover usuário | `sudo sqlite3 /opt/mapa/data/mapa.db "delete from users where username='nome'"` |
| Ver se está no ar | `sudo systemctl status mapa` |
| Ver erros | `sudo journalctl -u mapa -n 50 --no-pager` |
| Reiniciar | `sudo systemctl restart mapa` |
| Atualizar o código | `cd /opt/mapa && sudo git pull && sudo systemctl restart mapa` (ou copie os arquivos novos e reinicie) |

**Backup diário (2h da manhã, guarda 14 dias):**
```bash
sudo -u mapa mkdir -p /opt/mapa/backups
sudo crontab -u mapa -e
# adicione a linha:
0 2 * * * sqlite3 /opt/mapa/data/mapa.db ".backup '/opt/mapa/backups/mapa-$(date +\%F).db'" && find /opt/mapa/backups -name '*.db' -mtime +14 -delete
```
Copie a pasta `backups` para fora da VM de vez em quando. Os dados também podem ser salvos pelo botão **Exportar** do site.

## 7. Segurança

- Senhas guardadas com hash (nunca em texto). Mínimo de 10 caracteres.
- Sessão por cookie `HttpOnly` e `SameSite=Strict`, com validade de 12 horas.
- Bloqueio de 5 minutos após 5 tentativas de login erradas (por IP).
- Todas as rotas de dados exigem login.
- **Nunca envie ao GitHub** a pasta `data/` (banco e `secret.key`). O `.gitignore` já protege.
- **Não guarde senhas de computadores no site.** O botão do AnyDesk só usa o ID.
- O repositório contém o endereço interno do Zabbix (`10.78.4.7`). **Prefira deixar o repositório privado.**

## 8. Dados e API

**Estado do mapa** (JSON): 8 andares, cada um com uma lista de salas.
```
{ "floors": [ [ { "id", "name", "pcs": [ Dispositivo ] } ], ... ] }   // 8 itens: Térreo, 1º ... 7º
Dispositivo: { id, worker, tag, type, status, setor,
               users: [texto],
               cfg: { host, ip, anydesk, mac, modelo, serie, so, fw, vlan, notas, obs },
               extra: [ { k, v } ],
               occ: [ { id, ts, by, problema, solucao, situacao } ] }
```
Tipos: Computador, Notebook, Roteador, Switch, Access Point, Impressora, Servidor, Outro.
Status: Ativo, Em manutenção, Em estoque, Desativado.

| Rota | Função |
|---|---|
| `GET /` | site (exige login) |
| `GET /login.html` | tela de login |
| `POST /api/login` / `POST /api/logout` | entrar / sair |
| `GET /api/me` | usuário logado |
| `GET /api/state` / `PUT /api/state` | ler / gravar o mapa |
| `GET /api/history?device=ID&limit=N` | histórico (geral ou de um dispositivo) |

## 9. Limitações conhecidas

- **Gravação do mapa inteiro:** se duas pessoas editarem ao mesmo tempo, vale a última gravação.
- **Sem perfis de acesso:** todo usuário logado pode editar e apagar.
- **Zabbix:** o botão abre `http://10.78.4.7/zabbix/...`, endereço da rede interna. Só funciona para quem estiver na rede da empresa ou em uma VPN que alcance esse IP.
- **AnyDesk:** o botão usa o formato do AnyDesk padrão (`anydesk:ID`) e exige o AnyDesk instalado no computador de quem clica. O acesso sem aprovação depende do acesso autônomo configurado em cada máquina.
- O servidor roda em uma VM no computador pessoal: o site só fica no ar com a VM ligada.

## 10. Ideias para o futuro

Importar planilha Excel/CSV, perfis de acesso (administrador, analista, só leitura), dados de compra e garantia, relatórios em Excel/PDF, etiqueta com QR code, planta baixa de verdade, HTTPS pelo Tailscale e backup automático para fora da VM.

## 11. Histórico do projeto (resumo)

1. Protótipo do mapa (Térreo ao 7º) com salas e computadores.
2. Tela da sala em tela cheia, dispositivos em ícones, ficha somente leitura com edição à parte.
3. Botão "Acessar Remotamente" (AnyDesk) e campo ID Anydesk.
4. Paleta "vermelho acinzentado" com degradês.
5. Publicação no Ubuntu Server com banco SQLite, login e acesso por Tailscale.
6. Histórico, busca completa, ocorrências, status e alerta de IP duplicado.
7. Setor/Sala, Notas e "Aplicar Preferências Anteriores".
8. Painel inicial (dashboards + avisos) e botão Zabbix.
9. Cadastro/edição unificado, pesquisa dentro da sala.
10. **Removido:** o monitoramento do player de TV e rádio do Portal Cultura (decisão do usuário).
