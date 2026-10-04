"""Testes do motor: python tests/test_motor.py  (ou python -m pytest tests). O teste.py precisa de pandas."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
from truecoral.motor import analisar, montar_chips  # noqa: E402

EX = RAIZ / "tests" / "exemplos"


def _chips(r, n):
    return [c["texto"] for c in r["linhas"][str(n)]["chips"]]


def test_teste():
    r = montar_chips(analisar(EX / "teste.py"))
    assert r["erro"] is None and r["limite"] is None
    assert "↻ 4 voltas · terminou a sequência" in _chips(r, 7)
    assert "= 3 → 10 → 20 → 35 final · int" in _chips(r, 8)
    assert "↻ 10000 voltas · saiu: condição falsa" in _chips(r, 11)
    assert "↻ 5 voltas · saiu pelo break · linha 18" in _chips(r, 15)
    assert "True ×1 · False ×4" in _chips(r, 17)
    assert "! 1 vazio (NaN) em peso" in _chips(r, 20)
    assert "mean() usou 2 de 3 valores" in r["linhas"]["21"]["detalhe"]
    assert "› 305.25" in _chips(r, 22)


def test_infinito_para_no_limite():
    r = montar_chips(analisar(EX / "infinito.py", limite_tempo=1.5))
    assert r["limite"] is not None
    assert any("parou no limite" in c for c in _chips(r, 2))


def test_erro_no_meio():
    r = montar_chips(analisar(EX / "erro.py"))
    assert r["erro"]["tipo"] == "TypeError" and r["erro"]["linha"] == 7
    assert "✕ TypeError" in _chips(r, 7)
    assert _chips(r, 8) == []                       # depois do erro: nada, nem "não rodou"


def test_sintaxe():
    r = montar_chips(analisar(EX / "sintaxe.py"))
    assert r["erro"]["tipo"] == "SyntaxError" and r["erro"]["linha"] == 2


if __name__ == "__main__":
    for nome, f in list(globals().items()):
        if nome.startswith("test_"):
            f()
            print("ok ", nome)
