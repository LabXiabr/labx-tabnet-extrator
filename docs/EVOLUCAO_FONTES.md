# Evolucao para multiplas fontes e historico persistente

## Estado de implementacao

- **Homologada**: SIA/AM, grupo 06, para os periodos efetivamente testados.
- **Planejada**: SIA/PA, sem URL ou mapeamento confirmado. Intencionalmente bloqueada para extracao.
- O catalogo `configuracoes/fontes/*.json` registra metadados basicos, mas **nao transforma automaticamente** o executor SIA/AM em um executor de outros subsistemas.
- O fluxo GitHub Actions existente continua inalterado nesta etapa.

## Comandos

```bash
python scripts/catalogo_fontes.py validar
python scripts/catalogo_fontes.py listar
python scripts/catalogo_fontes.py detalhar --sistema SIA --subsistema AM
python -m pytest tests/test_catalogo_fontes.py -q
```

## Gerar proveniencia local (sem sobrescrita)

```bash
python scripts/gerar_proveniencia.py \
  --sistema SIA --subsistema AM --competencia 2009-04 \
  --csv dados/execucoes/sia_am_200904/normalizado.csv \
  --saida /tmp/labx_proveniencia_200904.json
```

A proveniencia registra o arquivo CSV, seu SHA-256, a URL e a configuracao cadastradas, o commit e o run ID quando presentes. Ela **nao afirma** que os valores foram consultados agora nem substitui o manifesto mensal existente.

## Proximas entregas obrigatorias

1. Inspecionar o formulario real SIA/PA, descobrir URL e parametros corretos e documentar indicadores e dimensoes. Nao inventar URL nem converter ausencia em zero.
2. Implementar o adaptador de consulta SIA/PA com validacao independente e testes, preservando o fluxo de SIA/AM.
3. Generalizar o executor e o workflow para receber sistema e subsistema, recusando fontes nao homologadas. Usar chave composta (fonte, parametros, competencia), nao apenas competencia.
4. Historico de longo prazo: definir versao imutavel (fonte + consulta + competencia + instante UTC + SHA), publicar releases com permissao minima e verificacao de integridade, politica de backup externo e teste de recuperacao. O repositorio nao deve regravar tags historicas ou publicar antes da validacao completa.
5. Homologar segunda fonte, comparacao e documentacao de reproducao.

## Criterios para ativar fonte

- Formulario original e seus parametros verificados.
- Exemplo real salvo; arquivo fonte e normalizado rastreaveis.
- Resultado comparado com referencia independente quando disponivel.
- Ausencias e indicadores devidamente explicados.
- Testes automatizados aprovados.
