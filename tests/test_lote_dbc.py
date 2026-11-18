import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import lote_dbc as l

class TestLote(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogo=json.loads((Path(__file__).resolve().parents[1]/'catalogo/fontes_sus.json').read_text())

    def test_planilha_mapeada(self):
        self.assertIn('SINAN/DENG',self.catalogo['fontes'])
        self.assertIn('SIA/PA',self.catalogo['fontes'])
        self.assertIn('SIH/RD',self.catalogo['fontes'])
        self.assertIn('CNES/ST',self.catalogo['fontes'])
        self.assertNotIn('CNES_ST/ST',self.catalogo['fontes'])

    def test_ano_completo(self):
        self.assertEqual(len(l.competencias('2009')),12)
        self.assertEqual(l.competencias('2009-04'),['2009-04'])
        for invalido in ('2009-13','2099','abc','2009-4'):
            with self.assertRaises(ValueError): l.competencias(invalido)

    def test_lista_todas_ufs_sem_filtro_manual(self):
        itens=l.filtrar_arquivos(['PAAC0904.dbc','PAGO0904.DBC','PASP0904.dbc','PAZZ0904.dbc','PAAC0905.dbc','AMAC0904.dbc'], 'PA','2009-04')
        self.assertEqual([u for u,_ in itens],['AC','GO','SP'])

    def test_mapeamento_tem_periodos(self):
        reg=l.fonte(self.catalogo,'SIA/PA')
        urls=l.urls_para_competencia(reg,'2009-04')
        self.assertEqual(len(urls),1)
        self.assertIn('200801_',urls[0])

    def test_nao_executa_fontes_sem_endereco(self):
        with self.assertRaises(ValueError):l.fonte(self.catalogo,'SINAN/DENG')

    def test_sinaliza_endereco_que_exige_revisao(self):
        with self.assertRaises(ValueError):l.fonte(self.catalogo,'SIM/DO')

    def test_descoberta_mock(self):
        reg=l.fonte(self.catalogo,'SIA/PA')
        plano=l.descobrir(reg,'SIA/PA','2009-04',lambda url:['PAAC0904.dbc','PAGO0904.dbc'])
        self.assertEqual(len(plano),2)
        self.assertEqual(plano[0]['uf'],'AC')

if __name__=='__main__':unittest.main()

class TestCompatibilidade(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.original = Path(self.tmp.name) / 'fontes.json'
        self.original.write_text(json.dumps({'fontes':[{
            'sistema':'SIA', 'subsistema':'PA','status':'piloto',
            'diretorio_ftp':'/dissemin/publicos/SIASUS/200801_/Dados',
            'prefixo':'PA','inicio':'2008-01'}]}))
        self.catalogo=json.loads((Path(__file__).resolve().parents[1]/'catalogo/fontes_sus.json').read_text())
    def tearDown(self): self.tmp.cleanup()
    def test_compatibilidade_valida(self):
        reg=self.catalogo['fontes']['SIA/PA']
        itens=[{'uf':'AC','competencia':'2009-04','url_diretorio':'ftp://ftp.datasus.gov.br/dissemin/publicos/SIASUS/200801_/Dados/','arquivo':'PAAC0904.dbc'}]
        self.assertEqual(l.verificar_compatibilidade_robo('SIA/PA',reg,['2009-04'],itens,self.original), [('AC','2009-04')])
    def test_fonte_nova_bloqueada(self):
        reg=self.catalogo['fontes']['CNES/ST']
        with self.assertRaisesRegex(ValueError,'apenas descoberta'):
            l.verificar_compatibilidade_robo('CNES/ST',reg,['2009-04'],[],self.original)
    def test_particoes(self):
        itens=l.filtrar_arquivos(['PAAC0904a.dbc','PAAC0904b.dbc','PAAC0904.dbc','PAAC0905.dbc'],'PA','2009-04')
        self.assertEqual(len(itens),3)
    def test_nao_reexecutar_particoes(self):
        reg=self.catalogo['fontes']['SIA/PA']
        itens=[{'uf':'AC','competencia':'2009-04','url_diretorio':'ftp://ftp.datasus.gov.br/dissemin/publicos/SIASUS/200801_/Dados/','arquivo':f'PAAC0904{suffix}.dbc'} for suffix in ('a','b')]
        self.assertEqual(len(l.verificar_compatibilidade_robo('SIA/PA',reg,['2009-04'],itens,self.original)),1)
    def test_limite(self):
        reg=self.catalogo['fontes']['SIA/PA']
        itens=[{'uf':'AC','competencia':f'2009-{m:02d}','url_diretorio':'ftp://ftp.datasus.gov.br/dissemin/publicos/SIASUS/200801_/Dados/','arquivo':'PAAC0904.dbc'} for m in range(1,13)]
        itens += [{'uf':'GO','competencia':f'2009-{m:02d}','url_diretorio':'ftp://ftp.datasus.gov.br/dissemin/publicos/SIASUS/200801_/Dados/','arquivo':'PAGO0904.dbc'} for m in range(1,13)]
        itens += [{'uf':'SP','competencia':f'2009-{m:02d}','url_diretorio':'ftp://ftp.datasus.gov.br/dissemin/publicos/SIASUS/200801_/Dados/','arquivo':'PASP0904.dbc'} for m in range(1,13)]
        with self.assertRaisesRegex(ValueError,'Execução bloqueada'):
            l.verificar_compatibilidade_robo('SIA/PA',reg,[f'2009-{m:02d}' for m in range(1,13)],itens,self.original)
