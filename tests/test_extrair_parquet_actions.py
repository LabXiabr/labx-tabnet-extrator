import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'extrair_parquet_actions.py'
spec = importlib.util.spec_from_file_location('extrair_parquet_actions', PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class TestExtracaoReal(unittest.TestCase):
    def test_ano_mensal(self):
        self.assertEqual(len(m.competencias('2010')), 12)
        self.assertEqual(m.competencias('2010-04'), ['2010-04'])
        with self.assertRaises(ValueError): m.competencias('2010-13')

    def test_matriz_anual(self):
        with patch.object(m, 'fonte_compativel', return_value={}):
            dados = m.matriz('SIA/PA', '2010')
        self.assertEqual(len(dados['include']), 108)
        self.assertEqual(dados['include'][0]['ufs'], 'AC-AL-AM')
        self.assertEqual(dados['include'][-1]['competencia'], '2010-12')

    def test_matriz_mes(self):
        with patch.object(m, 'fonte_compativel', return_value={}):
            dados = m.matriz('SIA/PA', '2010-04')
        self.assertEqual(len(dados['include']), 9)
        self.assertEqual(sum(len(x['ufs'].split('-')) for x in dados['include']), 27)

    def test_fonte_habilitada(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            amp = p/'amp.json'; ori=p/'ori.json'
            amp.write_text(json.dumps({'fontes':{'SIA/PA':{'sistema':'SIA','subsistema':'PA', 'diretorios':[{'url':'ftp://ftp.datasus.gov.br/dissemin/publicos/SIASUS/200801_/Dados/'}], 'revisao_necessaria':False}}}))
            ori.write_text(json.dumps({'fontes':[{'sistema':'SIA','subsistema':'PA','prefixo':'PA','diretorio_ftp':'/dissemin/publicos/SIASUS/200801_/Dados','status':'piloto','inicio':'2008-01'}]}))
            self.assertTrue(m.fonte_compativel('SIA/PA',['2010-04'],amp,ori))
            with self.assertRaises(ValueError):m.fonte_compativel('CNES/ST',['2010-04'],amp,ori)

    def test_verificar_parquet_e_manifesto(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            arq=p/'teste.parquet';arq.write_bytes(b'parquet teste')
            manifesto={'sistema':'SIA','subsistema':'PA','uf':'AC','competencia':'2010-04','total_registros':12,'arquivos':[{'parquet':'teste.parquet','sha256_parquet':m.hash_arquivo(arq),'registros_dbf':12,'registros_parquet':12}]}
            (p/'manifesto.json').write_text(json.dumps(manifesto))
            self.assertEqual(m.conferir_saida(p,'SIA/PA','AC','2010-04'),12)
            arq.write_bytes(b'alterado')
            with self.assertRaises(RuntimeError):m.conferir_saida(p,'SIA/PA','AC','2010-04')

if __name__ == '__main__': unittest.main()
