# ETL Monitor

## Visão Geral

O **ETL Monitor** é uma aplicação para gerenciamento, agendamento e monitoramento de execuções ETL, integrando banco de dados Firebird e Google BigQuery. Possui interface web (Flask) e desktop (Tkinter), além de agendamento automático via APScheduler.

---

## Estrutura do Projeto

```
etl_py_api/
│
├── database/
│   ├── create_database.py
│   ├── db_utils.py
│   ├── models.py
│   └── instance/
│       └── (db)
│
├── libs/
│   └── (DLLs e dependências nativas)
│
├── logs/
│   ├── controlador.log
│   └── etl_execution.log
│
├── scripts/
│   └── extract.py
│
├── server/
│   └── controlador.py
│
├── web/
│   ├── blueprints/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── etl.py
│   │   ├── logs.py
│   │   ├── permissions.py
│   │   ├── schedules.py
│   │   └── users.py
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css
│   │   ├── js/
│   │   │   └── scripts.js
│   │   └── img/
│   │       └── icone.svg
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── login.html
│   │   ├── manage_users.html
│   │   ├── manage_schedules.html
│   │   ├── execution_logs.html
│   │   ├── change_password.html
│   │   └── partials/
│   │       ├── _navbar.html
│   │       ├── _messages.html
│   │       ├── _table.html
│   │       ├── _pagination.html
│   │       ├── _form_create_user.html
│   │       ├── _form_create_schedule.html
│   │       └── _form_change_password.html
│   ├── cert.pem
│   ├── key.pem
│   └── monitor.py
│
├── .gitignore
├── LICENSE
├── main.py
└── README.md
```

---

## Funcionalidades Principais

1. **Gerenciamento de Agendamentos ETL**
   - Cadastro, edição e exclusão de agendamentos ETL via interface web.
   - Cada agendamento associa uma origem, script e destino, além de uma expressão CRON para periodicidade.
   - Permite ativar/desativar agendamentos.

2. **Execução Automática e Manual de ETL**
   - Execução automática dos agendamentos via APScheduler.
   - Execução manual de ETL, permitindo selecionar agendamento ou informar origem, script e destino manualmente.
   - Execução é feita em thread + subprocesso, isolando o processamento.

3. **Monitoramento de Execuções**
   - Dashboard web mostra todas as execuções recentes, com status, horários e registros processados.
   - Filtros por status e datas.
   - Atualização automática da tabela de execuções.

4. **Logs Detalhados**
   - Logs de execução salvos em arquivo e banco de dados.
   - Detalhes de cada execução, incluindo erros, parâmetros e quantidade de registros processados.

5. **Controle de Usuários**
   - Cadastro, edição, exclusão e alteração de senha de usuários.
   - Controle de permissões por usuário: cada usuário pode ter acesso apenas a determinadas origens, scripts e destinos.

6. **Controle de Permissões**
   - Interface para gerenciar permissões de acesso (origem, script, destino) por usuário.
   - Backend valida permissões antes de permitir execução manual ou agendada.

7. **Interface Web Moderna**
   - Interface responsiva com Bootstrap.
   - Formulários dinâmicos (JS) para seleção de scripts/destinos conforme origem e permissões.
   - Notificações de sucesso/erro.

8. **Interface Desktop (Tkinter)**
   - Aplicativo desktop para controle do servidor, logs e gerenciamento rápido.
   - Ícone na bandeja do sistema, controle de start/stop do servidor Flask.

9. **Integração com Firebird e Google BigQuery**
   - Scripts ETL extraem dados do Firebird e carregam no BigQuery.
   - Parâmetros de conexão e scripts SQL configuráveis.

10. **Controle de Execução**
    - Botão para parar ETL em execução (flag de stop).
    - Impede múltiplas execuções simultâneas do mesmo agendamento.

11. **Segurança**
    - Autenticação de usuários (Flask-Login).
    - CSRF protection nos formulários.
    - Permissões de acesso a recursos.

12. **Logs e Auditoria**
    - Logs de todas as ações importantes (execução, permissões, usuários).
    - Auditoria de quem executou o quê e quando.

---

## Fluxos de Uso

- **Usuário Admin** cadastra origens, scripts, destinos, usuários e permissões.
- **Usuário comum** só vê, agenda e executa o que tem permissão.
- **Execução manual:** usuário pode rodar ETL na hora, escolhendo recursos permitidos.
- **Execução agendada:** sistema executa automaticamente conforme CRON.
- **Monitoramento:** todos acompanham status, logs e resultados das execuções.

---

## Tecnologias Utilizadas

- **Flask** (web, blueprints, login, CSRF)
- **SQLAlchemy** (ORM)
- **APScheduler** (agendamento)
- **Tkinter** (desktop)
- **Firebird** (origem dos dados)
- **Google BigQuery** (destino dos dados)
- **Bootstrap** (frontend)
- **Threading/Subprocess** (execução isolada)
- **Logging** (logs detalhados)
- **Custom JS** (dinamismo nos formulários)

---

## Resumo

O projeto é um **monitor ETL completo**, com:
- Agendamento e execução de ETL
- Controle de permissões
- Monitoramento e logs
- Interface web e desktop
- Integração Firebird ↔ BigQuery
- Segurança e auditoria

---

## Requisitos

- Python 3.11+
- Firebird Client
- Google Cloud SDK (para BigQuery)
- Dependências Python (ver `requirements.txt`)

---

## Instalação

1. Clone o repositório:
    ```sh
    git clone https://github.com/lynconlmo/etl-fb-bq.git
    cd etl-monitor
    ```

2. Instale as dependências:
    ```sh
    pip install -r requirements.txt
    ```

3. Inicie a aplicação para gerar o banco de dados automaticamente:

  Ao executar o sistema pela primeira vez (`python main.py`), o banco de dados será criado automaticamente, assim como um usuário admin inicial. Após esse processo, você poderá acessar tanto a interface web quanto a desktop utilizando esse usuário, e então cadastrar novas origens, destinos, scripts, tabelas, usuários e permissões conforme necessário.


---

## Uso

- **Interface Desktop:**  
  Execute:
  ```sh
  python main.py
  ```
- **Interface Web:**  
  O servidor Flask será iniciado automaticamente e pode ser acessado via navegador.

- **Agendamentos:**  
  Os agendamentos são configurados via interface e executados automaticamente pelo APScheduler.

---

## Empacotamento

Para gerar um executável, utilize PyInstaller ou cx_Freeze.  
Garanta que todos os arquivos de configuração, banco, templates e DLLs estejam incluídos.

---

## Licença

MIT

---

## Contato

Dúvidas ou sugestões: [lyncon.oliveira.tads@gmail.com](mailto:lyncon.oliveira.tads@gmail.com)
