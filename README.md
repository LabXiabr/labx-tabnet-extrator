# LABX TabNet Extrator

Ferramenta Python para extracao, normalizacao, validacao e
consolidacao de dados publicos do DATASUS TabNet.

## Objetivo

Automatizar consultas por competencia, preservar as fontes
originais e produzir conjuntos de dados estruturados,
com validacao cruzada e auditoria de integridade.

## Escopo atual

O MVP implementa a fonte:

- Sistema: SIA
- Subsistema: AM
- Descricao: Producao Ambulatorial - Medicamentos
- Grupo de procedimento: 06
- Dimensoes: competencia e UF
- Indicador: quantidade aprovada

A arquitetura permite evolucoes, mas outras fontes ainda
precisam de implementacao e validacao especificas.

## Requisitos

- Python 3
- Acesso a internet para consultas publicas
- Dependencias listadas em requirements.txt

## Instalacao

Clone o repositorio e acesse sua pasta.

Crie um ambiente virtual:

    python3 -m venv .venv
    source .venv/bin/activate

Instale as dependencias:

    python -m pip install -r requirements.txt

Inicialize o formulario publico:

    python src/inicializar.py

A inicializacao preserva um formulario local existente.

## Planejar um intervalo

    python src/executar_intervalo.py \
      --sistema SIA \
      --subsistema AM \
      --inicio 2009-01 \
      --fim 2009-12 \
      --modo dinamico

Sem --executar, o comando apenas apresenta o planejamento.

## Executar consultas

Exemplo com limite de duas competencias pendentes:

    python src/executar_intervalo.py \
      --sistema SIA \
      --subsistema AM \
      --inicio 2009-04 \
      --fim 2009-05 \
      --modo dinamico \
      --executar \
      --limite 2

As consultas reais exigem confirmacao no terminal.

A execucao utiliza dados publicos do DATASUS e realiza
normalizacao, verificacao de qualidade e comparacao com
o CSV oficial.

## Consolidar resultados

Apos validar todas as competencias de um intervalo,
utilize a opcao --consolidar.

O executor nao deve sobrescrever resultados existentes.

## Auditoria

Cada nova competencia processada pelo executor de
intervalos gera um manifesto contendo hashes SHA-256
de cinco arquivos:

- Resposta HTML
- CSV normalizado
- Relatorio de qualidade
- Relatorio de validacao cruzada
- CSV oficial

O executor tambem verifica a integridade dos manifestos
mensais existentes antes de reutilizar competencias.

Os dados historicos de 2008 utilizam manifestos proprios.

## Testes

    python -m pytest -q

Observacao: parte dos testes atuais utiliza referencias
historicas armazenadas localmente em dados/. Uma
instalacao limpa pode precisar dessas referencias para
executar toda a suite.

## Armazenamento

A pasta dados/ guarda respostas, referencias, execucoes,
consolidados e manifestos gerados.

Essa pasta nao e versionada no Git por padrao.

## Limitacoes

- A implementacao atual suporta apenas SIA/AM.
- O modelo validado utiliza o grupo de procedimento 06.
- O formulario depende da disponibilidade do DATASUS.
- Consultas reais exigem confirmacao.
- A execucao possui limite configuravel de competencias.
- Falhas podem exigir analise antes da retomada.
- A compatibilidade de outras fontes e periodos deve ser validada.

## Aviso

Projeto independente desenvolvido com dados publicos
disponibilizados pelo DATASUS. Nao representa um sistema
oficial do Ministerio da Saude.
