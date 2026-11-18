#!/usr/bin/env python3
"""Regenera catálogo e relatório a partir da cópia CSV da aba subsistema.
O CSV é um retrato fiel dos valores da aba do XLSX recebido; atualize-o ao mudar a planilha.
Não valida URLs online; não marca nenhuma fonte como homologada.
"""
import collections
import csv
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / 'catalogo/subsistemas_origem.csv'
SAIDA = RAIZ / 'catalogo/fontes_sus.json'
RELATORIO = RAIZ / 'catalogo/relatorio_mapeamento.json'

def gerar():
    with ENTRADA.open(encoding='utf-8',newline='') as f:
        linhas=list(csv.DictReader(f))
    reg={}
    for linha in linhas:
        n=int(linha['linha_planilha'])
        if n in (1,83) or not linha['sistema'] or not linha['subsistema_ou_prefixo']:
            continue
        sis=linha['sistema'].strip().upper()
        sub=linha['subsistema_ou_prefixo'].strip().upper()
        sis_base=re.sub(r'\d+$','',sis).split('_',1)[0] if n<83 else sis
        codigo=f'{sis_base}/{sub}'
        r=reg.setdefault(codigo,dict(sistema=sis_base,subsistema=sub,nome='',variantes_origem=[],diretorios=[],origem_linhas=[],situacao='sem_diretorio_validado'))
        nome=linha['nome_ou_label'].strip()
        if nome and not r['nome']:r['nome']=nome
        r['origem_linhas'].append(n)
        if n<83:
            if sis not in r['variantes_origem']:r['variantes_origem'].append(sis)
        else:
            ftp=linha['ftp'].strip()
            if ftp.startswith('ftp://'):
                r['diretorios'].append(dict(url=ftp,linha_planilha=n))
    for codigo,r in reg.items():
        r['situacao']='diretorio_mapeado_na_planilha' if r['diretorios'] else 'sem_diretorio_validado'
        r['homologado']=False
        r['revisao_necessaria']=False
        if codigo in ('SIM/DO','SIM/DOEXT','SIM/DOFET','SIM/DOINF','SIM/DOMAT'):
            r['revisao_necessaria']=True
            r['observacao']='Conferir URL/prefixo e regras específicas SIM antes de executar; há divergências aparentes na planilha.'
        if codigo=='SIA/PA':
            r['observacao']='Há mais de um diretório, variando por período; verificar competência antes de baixar.'
        if codigo=='SINASC/DNRIG':r['revisao_necessaria']=True
    reg=dict(sorted(reg.items()))
    catalogo=dict(schema_version=1,origem=dict(arquivo='dicionario_mapaDadosAbertosSUS2025-02-12 (1).xlsx',aba='subsistema',observacao='Catálogo extraído da planilha, não comprovação de disponibilidade online ou homologação.'),fontes=reg)
    relatorio=dict(total_fontes=len(reg),sistemas=dict(sorted(collections.Counter(x['sistema'] for x in reg.values()).items())),com_diretorio=sum(bool(x['diretorios']) for x in reg.values()),sem_diretorio=sum(not x['diretorios'] for x in reg.values()),revisao_necessaria=[k for k,v in reg.items() if v['revisao_necessaria']],observacao='Fonte planilha; condições de publicação online não verificadas.')
    SAIDA.write_text(json.dumps(catalogo,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    RELATORIO.write_text(json.dumps(relatorio,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Catálogo atualizado: {len(reg)} fontes')

if __name__=='__main__':gerar()
