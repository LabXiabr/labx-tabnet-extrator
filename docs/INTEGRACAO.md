# Checklist de integração sem afetar a PoC existente

1. Confirmar branch de trabalho (`git switch -c feat/catalogo-fontes-lote`).
2. Copiar arquivos do pacote para a raiz; **não substituir** `poc_dbc_online/robo.py`, `poc_dbc_online/fontes.json` nem `.github/workflows/poc-dbc-online.yml`.
3. Rodar testes deste pacote e os testes atuais (`python -m pytest -q`, se pytest já está configurado).
4. Confirmar argumentos reais do robô (`python poc_dbc_online/robo.py --help`). Se diferirem, ajustar a lista `cmd` em `scripts/lote_dbc.py` antes de executar.
5. Rodar primeiro com `--fonte SIA/PA --competencia 2009-04` **sem** `--executar` e conferir `poc_dbc_online/saidas/plano_lote.json`.
6. Conferir padrões de nomes de arquivo e FTP a partir dos resultados reais antes de habilitar novas fontes. Algumas séries têm nomes e diretórios diferentes dos padrões mensais.
7. Garantir que `.gitignore` exclui `poc_dbc_online/saidas/`, arquivos `.dbc`, `.dbf`, `.parquet`, `.duckdb`, segredos e volumes grandes. Não remover arquivos do repositório automaticamente.
8. Se o repositório tiver requisitos de proteção de dados, seguir as regras internas LABX e evitar publicar resultados brutos como artefatos de Actions.
9. Executar PoC controlada e confrontar contagem, colunas e hashes com o teste de referência SIA/PA AC 2009-04 (45.924 registros; 54 colunas), lembrando que disponibilidade ou versão oficial podem mudar.
10. Só abrir PR após verificar os resultados de integração e que os scripts existentes permanecem intactos.

## Observação sobre múltiplas UFs e períodos

A busca usa todos os arquivos do diretório FTP que obedecem ao padrão do subsistema e competência; não exige UF digitada. Uma execução anual pode envolver centenas de arquivos. A descoberta do FTP de cada mês repete a listagem de diretório (comportamento simples e transparente, ainda sem cache).

## Atualização do dicionário

O CSV é um retrato da aba `subsistema`; para alterações futuras, exporte novamente essa aba preservando as colunas e linhas, ou atualize cuidadosamente `subsistemas_origem.csv` com seu número original de linha. Depois rode `python scripts/atualizar_catalogo.py`. O script não tenta inferir novos diretórios ou corrigir dados possivelmente errados.
