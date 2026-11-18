import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from poc_dbc_online import robo


class TestCatalogo(unittest.TestCase):
    def test_piloto_sia_pa(self):
        f = robo.obter_fonte('SIA', 'PA')
        self.assertEqual(f['prefixo'], 'PA')
        self.assertEqual(robo.validar_entrada(f, 'AC', '2009-04'), 'AC')

    def test_planejada_bloqueada(self):
        with self.assertRaises(ValueError):
            robo.obter_fonte('SIM', 'DO')

    def test_uf_invalida(self):
        with self.assertRaises(ValueError):
            robo.validar_entrada(robo.obter_fonte('SIA', 'PA'), 'XX', '2009-04')

    def test_periodo_invalido(self):
        with self.assertRaises(ValueError):
            robo.validar_entrada(robo.obter_fonte('SIA', 'PA'), 'AC', '2009-13')

    def test_descobre_particoes_remotas(self):
        f = robo.obter_fonte('SIA', 'PA')
        nomes = ['PAAC0904.dbc', 'PAAC0904a.DBC', 'PAGO0904.dbc', 'PAAC0905.dbc']
        self.assertEqual(robo.selecionar_arquivos(nomes, f, 'AC', '2009-04'),
                         ['PAAC0904.dbc', 'PAAC0904a.DBC'])

    def test_nao_encontra_nao_inventa(self):
        with self.assertRaises(FileNotFoundError):
            robo.selecionar_arquivos([], robo.obter_fonte('SIA', 'PA'), 'AC', '2009-04')

    def test_download_completo_e_hash(self):
        with TemporaryDirectory() as td:
            ftp = Mock()
            conteudo = b'DBC-de-teste'
            ftp.size.return_value = len(conteudo)
            ftp.retrbinary.side_effect = lambda cmd, callback, blocksize: callback(conteudo)
            arquivo = Path(td) / 'PAAC0904.dbc'
            self.assertEqual(robo.baixar(ftp, 'PAAC0904.dbc', arquivo, 100), len(conteudo))
            self.assertEqual(robo.hash_arquivo(arquivo), hashlib.sha256(conteudo).hexdigest())

    def test_download_truncado_nao_promove(self):
        with TemporaryDirectory() as td:
            ftp = Mock()
            ftp.size.return_value = 100
            ftp.retrbinary.side_effect = lambda cmd, callback, blocksize: callback(b'curto')
            arquivo = Path(td) / 'PAAC0904.dbc'
            with self.assertRaises(IOError):
                robo.baixar(ftp, 'PAAC0904.dbc', arquivo, 100)
            self.assertFalse(arquivo.exists())


if __name__ == '__main__':
    unittest.main()
