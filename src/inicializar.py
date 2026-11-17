import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

INSPECAO = (
    RAIZ / "dados/inspecao/formulario_sia_qabr.json"
)

MODELO = (
    RAIZ / "configuracoes/modelos/sia_am_base.json"
)

URL = (
    "https://tabnet.datasus.gov.br/cgi/"
    "deftohtm.exe?sia/cnv/qabr.def"
)


def main():
    print("=== INICIALIZACAO LABX TABNET ===")

    if not MODELO.is_file():
        raise SystemExit(
            f"Modelo de consulta ausente: {MODELO}"
        )

    if INSPECAO.is_file():
        print("Formulario local ja disponivel.")
        print("Nenhum download necessario.")
        return

    print("Obtendo formulario publico DATASUS.")

    subprocess.run(
        [
            sys.executable,
            str(
                RAIZ / "src/core/inspecionar_formulario.py"
            ),
            URL,
        ],
        cwd=RAIZ,
        check=True,
    )

    if not INSPECAO.is_file():
        raise SystemExit(
            "Falha: inspecao nao foi gerada."
        )

    print("Inicializacao concluida.")


if __name__ == "__main__":
    main()
