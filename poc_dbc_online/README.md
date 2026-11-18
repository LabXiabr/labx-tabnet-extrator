# PoC independente: DATASUS DBC -> Parquet usando DuckDB

Esta pasta e o workflow `.github/workflows/poc-dbc-online.yml` sao uma integracao **aditiva** ao repositorio `labx-tabnet-extrator`. Nao mudam os scripts de TabNet nem as fontes homologadas ja existentes.

## Objetivo do piloto

1. A cada execucao, abrir conexao nova ao **FTP oficial DATASUS**, listar o diretorio da fonte e identificar os DBCs para sistema/subsistema/UF/competencia.
2. Baixar novamente os DBCs selecionados (sem cache e sem comparacao com execucoes anteriores).
3. Converter DBC -> DBF com `dbc-to-dbf`; ler DBF em streaming com `dbfread`; preparar CSV **temporario** com todos os campos como texto; escrever Parquet com DuckDB.
4. Validar bytes baixados, SHA-256 da origem e equivalencia de contagem DBF vs Parquet, e gerar `manifesto.json`.
5. Disponibilizar Parquet + manifesto como artefato temporario do Actions (tres dias), sem armazenamento historico persistente.

**Apenas SIA/PA e piloto experimental**. SIA/AM e SIH/RD sao rotas de descoberta experimentais, sem homologacao de layout/indicadores. SIM/DO permanece planejada e bloqueada ate se verificar sua estrutura de diretorios. A presenca no catalogo nao equivale a homologacao.

**Nao reproduz ainda a ETL de Felipe nem valida os indicadores no TabNet.** Parquet gerado e camada bruta, nao produto analitico homologado. Os valores sao mantidos como texto para preservar codigos; dimensoes, tipos e indicadores de negocio devem ser tratados numa camada posterior com mapeamento auditavel.

## Rodar localmente (WSL / servidor)

Na raiz do repo:

```bash
python3 -m venv .venv  # somente se nao existir
source .venv/bin/activate
python -m pip install -r poc_dbc_online/requirements.txt
python -m unittest discover -s poc_dbc_online/tests -v
python -m poc_dbc_online.robo --sistema SIA --subsistema PA --uf AC --competencia 2009-04 --saida poc_dbc_online/saidas
```

Exemplo com uma UF/competencia; somente executa quando o DBC estiver realmente presente no FTP e o servico estiver acessivel. O endereco FTP pode estar indisponivel em determinados ambientes de CI; uma falha de conexao nao deve ser confundida com ausência de arquivos.

## Rodar GitHub Actions

Actions -> `PoC DBC online para Parquet (DATASUS)` -> Run workflow. Na primeira rodada: SIA, PA, AC, 2009-04. O Actions requer acesso externo ao FTP via porta 21, que pode falhar por restricoes de rede do runner. Se falhar, testar na Pipeta/WSL ou considerar o transporte oficial alternativo, mantendo evidencia de origem. GitHub e ambiente de demonstracao, nao o armazenamento futuro.

## Resultados

`poc_dbc_online/saidas/sia_pa_ac_2009-04_<execucao>/` contem um Parquet para cada DBC encontrado, e `manifesto.json` contendo arquivos consultados, URLs FTP, momento da consulta, hashes, colunas e contagens. A cada rodada gera nova pasta; nao sobrescreve resultados anteriores da mesma pasta, mas nao depende deles para funcionar.

## Seguranca / limites

- Apenas FTP de hostname constante (`ftp.datasus.gov.br`) e caminhos de um catalogo versionado (nao aceita URL arbitraria pela CLI).
- Limite de 80 MiB por DBC no Actions; `--max-mb` permite ajustar ate 500 MiB localmente. Arquivos grandes podem superar as cotas do Actions e precisar de recursos do servidor.
- Nao enviar dados sensiveis ou credenciais a artefatos publicos; estes datasets sao fontes disseminadas publicamente, mas revisar governanca de publicacao.
- Preserva somente resultados completos; remove o diretorio incompleto se ocorrer falha. Temporarios removidos automaticamente. Nao toca em bancos de producao.
- Esta PoC nao implementa reprocessamento historico, transformacoes de dominio, filtragem de colunas ou conciliacao com TabNet; essas etapas exigem trabalho posterior.
- Conversor externo `dbc-to-dbf` e dependencia independente e deve passar por revisao de seguranca/licenca antes da implantacao institucional.

## Evolucao para Pipeta e Bureta

Executar o mesmo `python -m poc_dbc_online.robo` a partir da Pipeta com area de trabalho isolada; catalogo de fontes deve evoluir para uma fonte unica de configuracao com o TabNet; armazenar os Parquets posteriormente na Bureta com regras de permissao, retencao e validacao; acrescentar controle de qualidade do Felipe, tipos por subsistema e cron/Prefect conforme a infraestrutura.

Fontes tecnicas: https://duckdb.org/docs/stable/data/parquet/overview ; https://github.com/mozaru/dbc-to-dbf ; https://www.saude.rj.gov.br/comum/code/MostrarArquivo.php?C=NTIxNDU%2C
