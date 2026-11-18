# LABX TabNet Extrator — Entrega inicial DBC (sem conversão)

Este pacote substitui **somente** `.github/workflows/poc-dbc-lote-catalogo.yml` e adiciona o script `scripts/baixar_dbc_actions.py` e seus testes. Reutiliza `scripts/extrair_parquet_actions.py` e `scripts/gerar_opcoes_workflow.py` já presentes no projeto. O robô DBC→Parquet original é preservado, mas **não é executado por este workflow**.

## Funcionamento

Selecionar fonte (`SIA/PA`, `SIA/AM` ou `SIH/RD`) e competência (`2010-04` ou `2010`). O workflow divide mês/UF em lotes de 3 estados, lista o diretório oficial no FTP, baixa os `.dbc` sem alteração, valida tamanho do download e SHA-256 e disponibiliza `*.dbc`, `manifesto.json` e `resumo_lote.json` em **Artifacts**. Não faz conversão e não publica DBCs no Git. Uma execução anual de fonte mensal com 27 UFs cria até 108 jobs, com 2 em paralelo. O download e o upload ainda podem demorar conforme a rede e o tamanho dos arquivos; o GitHub também impõe quotas de armazenamento.

## Aplicar (WSL)

```bash
cd ~/projetos/labx-tabnet-extrator
unzip -oq '/mnt/c/Users/mylen/Downloads/LABX_download_DBC_20261118.zip' -d /tmp
cp -a /tmp/LABX_download_DBC_20261118/. .
python -m unittest discover -s tests -p 'test_baixar_dbc_actions.py' -v
python scripts/gerar_opcoes_workflow.py --check
python scripts/baixar_dbc_actions.py --fonte SIA/PA --competencia 2010-04 --matriz
```

## Cuidados

- Fazer primeiro um teste mensal com `SIA/PA` e `2010-04`. Conferir os `.dbc` nos artefatos de pelo menos um job.
- O GitHub Actions guarda os artefatos por 7 dias (configuração do workflow), não os mantém como armazenamento definitivo.
- Fontes da planilha não homologadas ficam no catálogo, mas fora deste formulário de extração.
- A primeira entrega **DBC** não inclui Parquet. Conversão poderá ser retomada em outra etapa.
- Há limite de segurança por DBC de 1 GiB e por lote de 6 GiB; arquivos maiores exigem revisão dessas proteções.
