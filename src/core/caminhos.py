import re


def nome_execucao(sistema, subsistema, competencia):
    sistema = sistema.strip().lower()
    subsistema = subsistema.strip().lower()

    if not re.fullmatch(r"[a-z]+", sistema):
        raise ValueError("Sistema invalido")

    if not re.fullmatch(r"[a-z]+", subsistema):
        raise ValueError("Subsistema invalido")

    if not re.fullmatch(
        r"[0-9]{4}-(0[1-9]|1[0-2])",
        competencia,
    ):
        raise ValueError("Competencia invalida")

    identificador = competencia.replace("-", "")

    return f"{sistema}_{subsistema}_{identificador}"
