from pathlib import Path
from bs4 import BeautifulSoup

arquivo = Path("dados/respostas/sia_am_200801.html")

html = arquivo.read_bytes()

soup = BeautifulSoup(
    html.decode("iso-8859-1", errors="replace"),
    "html.parser"
)

tabelas = soup.find_all("table")

print("TABELAS IDENTIFICADAS:", len(tabelas))

for numero, tabela in enumerate(tabelas, start=1):
    linhas = tabela.find_all("tr")

    print(f"\n===== TABELA {numero} =====")
    print("Linhas identificadas:", len(linhas))

    for linha in linhas[:8]:
        celulas = linha.find_all(
            ["th", "td"],
            recursive=False
        )

        valores = [
            celula.get_text(" ", strip=True)
            for celula in celulas
        ]

        if valores:
            print(" | ".join(valores[:30]))

print("\n=== INDICADORES ===")

texto = soup.get_text(" ", strip=True)

for termo in [
    "Jan/2008",
    "Medicamentos",
    "35.943",
    "36.088.068"
]:
    print(f"{termo}: {termo in texto}")
