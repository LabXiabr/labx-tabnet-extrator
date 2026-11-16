# Caso de teste — SIA/AM

## Fonte
DATASUS — TabNet SIA/SUS, por local de atendimento.

Formulário: sia/cnv/qabr.def

## Configuração

- Linha: Ano/mês_processamento
- Coluna: UF
- Indicador: Qtd.aprovada
- Filtro: Grupo procedimento 06 — Medicamentos
- Competência: janeiro de 2008

## Resultados validados

- Registros: 27 UFs
- Total nacional: 36.088.068
- Rondônia: 35.943
- Soma das UFs: igual ao total informado

## Saída

dados/saida/sia_am_200801.csv

## Testes

Quatro testes automatizados aprovados.

## Limitações

A implementação atual utiliza parâmetros fixos para janeiro de 2008.

Os testes validam o CSV produzido, mas ainda não cobrem respostas
inválidas, dados ausentes, mudanças no HTML ou múltiplas competências.
