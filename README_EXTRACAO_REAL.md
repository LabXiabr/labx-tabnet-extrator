# LABX — Extração real DBC → Parquet no GitHub Actions

## Objetivo da entrega

O workflow `PoC DBC - extracao real Parquet` **baixa os arquivos DBC**, converte com o `poc_dbc_online/robo.py` existente e publica **Parquets e manifestos** como artefatos. Não entrega somente o plano JSON.

## Escopo de segurança

- `catalogo/fontes_sus.json` permanece com as 82 fontes cadastradas. **Somente fontes presentes e compatíveis no `poc_dbc_online/fontes.json` original entram no dropdown da execução real** (inicialmente SIA/PA, SIA/AM, SIH/RD). As demais devem ser adaptadas e validadas antes de habilitar download/conversão.
- A competência aceita `AAAA-MM` (um mês) ou `AAAA` (12 meses). Todas as **27 UFs** são consideradas, sem digitação manual. Fontes com estrutura não estadual ainda exigem adaptação.
- Um mês gera **9 jobs**, cada um com até 3 UFs; um ano completo gera **108 jobs**. Somente **2 jobs paralelos** são executados. Cada job faz downloads e converte usando o robô original, com seus limites de 80 MB por arquivo DBC, verificações e manifestos.
- Os Parquets e manifestos gerados são publicados em **Actions → execução → Artifacts**; há um artefato por lote. Eles ficam disponíveis por 7 dias. Não são adicionados ao Git.
- Falhas de qualquer UF deixam o respectivo job vermelho e `resumo_lote.json` documenta os itens que falharam. Arquivos de UFs concluídas no mesmo lote ainda podem ser baixados, se o upload for possível.
- A validação de Parquet aqui confirma hash e contagem com o manifesto; **não é homologação semântica/TabNet**.

## Instalação

Na raiz `~/projetos/labx-tabnet-extrator` (WSL), com ZIP em Downloads:

```bash
unzip -oq '/mnt/c/Users/mylen/Downloads/LABX_extracao_real_20261118.zip' -d /tmp
cp -a /tmp/LABX_extracao_real_20261118/. ./
python -m unittest discover -s tests -p 'test_extrair_parquet_actions.py' -v
python scripts/gerar_opcoes_workflow.py --check
python scripts/extrair_parquet_actions.py --fonte SIA/PA --competencia 2010-04 --matriz > /tmp/labx-matriz.json
python -m json.tool /tmp/labx-matriz.json | head -25
git diff --check
```

**Não execute o comando sem `--matriz` localmente**, exceto para uma extração real deliberada; ele baixa DBCs e cria Parquets.

## Publicação

```bash
git add .github/workflows/poc-dbc-lote-catalogo.yml scripts/extrair_parquet_actions.py scripts/gerar_opcoes_workflow.py tests/test_extrair_parquet_actions.py README_EXTRACAO_REAL.md
git diff --cached --check
git diff --cached --stat
git commit -m 'feat: extracao real de DBC em lotes com Parquets no Actions'
git push origin HEAD
```

## Primeira execução recomendada

Em **Actions → PoC DBC - extracao real Parquet → Run workflow**, selecionar `main`, `SIA/PA` e `2010-04`. O workflow executará a conversão efetiva nas 27 UFs; são 9 jobs em lotes de 3 UFs. Após confirmar a conversão real e o tamanho dos artefatos, usar `2010` para os 12 meses — essa execução gera 108 jobs e pode consumir bastante tempo, minutos de Actions e armazenamento.

## Pré-requisitos e limites

- O repositório precisa conter `poc_dbc_online/robo.py`, `poc_dbc_online/fontes.json` e `poc_dbc_online/requirements.txt` compatível com `duckdb`, `dbfread` e `dbctodbf`. Se a conversão depende de outros binários do WSL, o runner Ubuntu do GitHub também precisará deles.
- GitHub-hosted runners têm limites de tempo, armazenamento e cota de minutos/artefatos. Essa implementação não usa armazenamento externo persistente; **baixar os artefatos antes do prazo de retenção**.
- O workflow usa o mecanismo de artefatos do GitHub para disponibilizar os Parquets; não os grava no repositório, nem realiza upload para a infraestrutura LABX. Para execução histórica em grande escala, armazenamento externo ou infraestrutura própria será necessário.
