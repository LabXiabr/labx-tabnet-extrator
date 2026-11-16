import argparse
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


BASE = "http://tabnet.datasus.gov.br/"


def validar_url(url):
    partes = urlparse(url)

    if (
        partes.scheme not in ("http", "https")
        or partes.hostname != "tabnet.datasus.gov.br"
        or partes.username is not None
        or partes.password is not None
        or partes.port not in (None, 80, 443)
        or not partes.path.startswith("/csv/")
        or not partes.path.lower().endswith(".csv")
        or partes.query
        or partes.fragment
    ):
        raise ValueError("URL CSV nao autorizada")


def baixar_csv(html_arquivo, destino):
    if destino.exists():
        raise FileExistsError(
            f"Arquivo ja existente: {destino}"
        )

    html = html_arquivo.read_bytes().decode(
        "iso-8859-1"
    )
    soup = BeautifulSoup(html, "html5lib")

    links = [
        a["href"]
        for a in soup.find_all("a", href=True)
        if "Copia como .CSV"
        in a.get_text(" ", strip=True)
    ]

    if len(links) != 1:
        raise ValueError(
            f"Links CSV encontrados: {len(links)}"
        )

    url = urljoin(BASE, links[0])
    validar_url(url)

    print("Fonte publica:", url)

    req = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urlopen(req, timeout=60) as resposta:
        validar_url(resposta.url)

        if resposta.status != 200:
            raise ValueError(
                f"HTTP inesperado: {resposta.status}"
            )

        conteudo = resposta.read(10_000_001)

    if not conteudo or len(conteudo) > 10_000_000:
        raise ValueError(
            "Resposta vazia ou acima do limite"
        )

    # CSV oficial do TabNet: cabecalho com dimensao.
    texto = conteudo.decode("iso-8859-1")

    if "Ano/mês processamento" not in texto:
        raise ValueError(
            "Resposta nao parece ser o CSV esperado"
        )

    destino.parent.mkdir(
        parents=True, exist_ok=True
    )
    destino.write_bytes(conteudo)

    print("CSV oficial baixado.")
    print("Arquivo:", destino)
    print("Tamanho:", len(conteudo), "bytes")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", required=True)
    parser.add_argument("--saida", required=True)
    args = parser.parse_args()

    baixar_csv(
        Path(args.html),
        Path(args.saida)
    )


if __name__ == "__main__":
    main()
