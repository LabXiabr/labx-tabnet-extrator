import importlib.util
import tempfile
import ftplib
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

CAMINHO = Path(__file__).resolve().parents[1] / 'scripts' / 'baixar_dbc_actions.py'
import sys
sys.path.insert(0, str(CAMINHO.parent))
spec = importlib.util.spec_from_file_location('baixar_dbc_actions', CAMINHO)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class TestDownloadDBC(unittest.TestCase):
    def test_arquivo_e_particoes(self):
        nomes = ['PAAC1004.dbc', 'PAAC1004a.dbc', 'PAAC1005.dbc', 'PAGO1004.dbc']
        self.assertEqual(m.selecionar(nomes, 'PA', 'AC', '2010-04'), ['PAAC1004.dbc', 'PAAC1004a.dbc'])

    def test_download_e_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            ftp = MagicMock()
            ftp.size.return_value = 3
            ftp.retrbinary.side_effect = lambda _cmd, callback, **_kwargs: callback(b'abc')
            arq = Path(tmp) / 'PAAC1004.dbc'
            info = m.baixar(ftp, arq.name, arq)
            self.assertEqual(arq.read_bytes(), b'abc')
            self.assertEqual(info['sha256_dbc'], m.sha256(arq))
            self.assertEqual(info['bytes_dbc'], 3)

    def test_download_incompleto_excluido(self):
        with tempfile.TemporaryDirectory() as tmp:
            ftp = MagicMock()
            ftp.size.return_value = 20
            ftp.retrbinary.side_effect = lambda _cmd, callback, **_kwargs: callback(b'abc')
            arq = Path(tmp) / 'PAAC1004.dbc'
            with self.assertRaises(OSError): m.baixar(ftp, arq.name, arq)
            self.assertFalse(arq.exists())
            self.assertFalse((Path(tmp) / 'PAAC1004.dbc.part').exists())

    def test_fechar_conexao_quebrada(self):
        ftp = MagicMock()
        ftp.close.return_value = None
        ftp.quit.side_effect = AttributeError('sem socket')
        m.fechar(ftp)
        ftp.close.assert_called_once()
        ftp.quit.assert_not_called()

    def test_conectar_reconecta_apos_timeout(self):
        erro = TimeoutError('timed out')
        primeiro, segundo = MagicMock(), MagicMock()
        primeiro.connect.side_effect = erro
        segundo.nlst.return_value = ['PAAC1004.dbc']
        with patch.object(m.ftplib, 'FTP', side_effect=[primeiro, segundo]), patch.object(m.time, 'sleep'):
            ftp, nomes = m.conectar('/teste')
        self.assertIs(ftp, segundo)
        self.assertEqual(nomes, ['PAAC1004.dbc'])
        primeiro.close.assert_called_once()

    def test_matriz_reutilizada(self):
        with patch.object(m, 'matriz', return_value={'include': []}):
            self.assertEqual(m.matriz('SIA/PA', '2010'), {'include': []})

if __name__ == '__main__':
    unittest.main()
