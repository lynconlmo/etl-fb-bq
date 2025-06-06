# ETL Monitor

## Visão Geral

O **ETL Monitor** é uma aplicação para gerenciamento, agendamento e monitoramento de execuções ETL, integrando banco de dados Firebird e Google BigQuery. Possui interface web (Flask) e desktop (Tkinter), além de agendamento automático via APScheduler.

---

## Estrutura do Projeto

```
etl_py_api/
│
├── database/
│   ├── db_utils.py
│   ├── models.py
│   └── instance/
│       └── etl_monitor.db
│
├── scripts/
│   └── extract.py
│
├── logs/
│   ├── controlador.log
│   └── etl_execution.log
│
├── web/
│   ├── blueprints/
│   ├── static/
│   ├── templates/
│   └── monitor.py
│
├── server/
│   └── controlador.py
│
├── libs/
│   └── (DLLs e dependências nativas)
│
├── main.py
└── README.md
```

---

## Funcionalidades

- **Cadastro e gerenciamento de agendamentos ETL**
- **Execução automática de scripts ETL**
- **Monitoramento de execuções**
- **Logs detalhados**
- **Interface web (Flask) e desktop (Tkinter)**
- **Integração com Firebird e Google BigQuery**
- **Controle de usuários e permissões**

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
    git clone https://github.com/seu-usuario/etl-monitor.git
    cd etl-monitor
    ```

2. Instale as dependências:
    ```sh
    pip install -r requirements.txt
    ```

3. Configure o banco de dados e arquivos de chave do BigQuery em `etl_base/json/`.

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
