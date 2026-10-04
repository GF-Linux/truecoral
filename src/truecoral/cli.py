"""O comando coral: roda o motor com o Python certo e desenha o arquivo com o que cada linha fez.

    coral arquivo.py                 o arquivo, linha a linha, com os chips ao lado
    coral arquivo.py --json          o resultado cru do motor (é o que a extensão do VS Code lê)
    coral arquivo.py --python P      roda com este Python
    coral arquivo.py --tempo 20      limite de tempo, em segundos (padrão: 10)
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from truecoral import __version__

MOTOR = Path(__file__).with_name("motor.py")

COR = {"azul": "38;2;74;163;239", "verde": "38;2;110;200;140", "lilas": "38;2;190;150;230",
       "amarelo": "38;2;240;180;60", "vermelho": "38;2;235;100;90", "cinza": "38;2;125;133;146",
       "borda": "38;2;74;80;90", "negrito": "1"}


def _tem_cor():
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def c(texto, *cores):
    if not _tem_cor() or not cores:
        return str(texto)
    return "".join(f"\x1b[{COR[k]}m" for k in cores) + str(texto) + "\x1b[0m"


def _largura(texto):
    import re
    return len(re.sub(r"\x1b\[[0-9;]*m", "", texto))


# ── qual Python roda o código ──────────────────────────────────────────────

def achar_python(arquivo, indicado=None):
    if indicado:
        return indicado
    for pasta in (Path(arquivo).resolve().parent, Path.cwd()):
        for nome in (".venv", "venv", "env"):
            py = pasta / nome / "bin" / "python"
            if (pasta / nome / "pyvenv.cfg").is_file() and py.exists():
                return str(py)
    if os.environ.get("VIRTUAL_ENV"):
        return str(Path(os.environ["VIRTUAL_ENV"]) / "bin" / "python")
    return shutil.which("python3") or shutil.which("python") or sys.executable


def rodar_motor(arquivo, python, tempo):
    r = subprocess.run([python, str(MOTOR), str(arquivo), "--tempo", str(tempo)],
                       capture_output=True, text=True, timeout=tempo + 30, cwd=os.getcwd())
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "o motor não respondeu")
    return json.loads(r.stdout)


# ── os chips ────────────────────────────────────────────────────────────────

def evolucao(v):
    h, total, ultimo = v["historico"], v["total"], v["ultimo"]
    if total == 1:
        return c(h[0], "azul", "negrito")
    if total <= len(h) + 1:
        passos = h + ([ultimo] if total > len(h) else [])
        return c(" → ".join(passos[:-1]) + " → ", "azul") + c(passos[-1], "azul", "negrito") + c(" final", "cinza")
    return (c(" → ".join(h) + " → … → ", "azul") + c(ultimo, "azul", "negrito")
            + c(f" final ({total}×)", "cinza"))


def chips(linha, n):
    partes = []
    laco = linha.get("laco")
    if laco:
        saida = laco["saida"]
        como = {"fim": "terminou a sequência", "condição falsa": "saiu: condição falsa",
                "break": f"saiu pelo break · linha {saida.get('linha')}",
                "limite": "parou no limite (laço infinito?)"}[saida["como"]]
        cor = "amarelo" if saida["como"] == "limite" else "lilas"
        partes.append(c(f"↻ {laco['voltas']} volta{'s' if laco['voltas'] != 1 else ''}", cor, "negrito")
                      + c(f" · {como}", cor))
    cond = linha.get("condicao")
    if cond and not (laco and laco["tipo"] == "while" and cond["False"] <= 1 and saida["como"] != "limite"):
        partes.append(c(f"True ×{cond['True']}", "verde") + c(" · ", "cinza") + c(f"False ×{cond['False']}", "vermelho"))
    valores = linha.get("valores", {})
    for nome, v in valores.items():
        rotulo = c(f"{nome}: ", "cinza") if (len(valores) > 1 or laco) else c("= ", "azul")
        partes.append(rotulo + evolucao(v) + c(f"  {v['tipo']}", "cinza"))
        if v.get("aviso"):
            partes.append(c(f"! {v['aviso']}", "amarelo"))
    if "saida" in linha:
        texto = linha["saida"].rstrip("\n").splitlines()
        primeira = texto[0] if texto else ""
        total = max(linha.get("linhas_saida", len(texto)), len(texto))
        extra = f"  (+{total - 1} linha{'s' if total - 1 != 1 else ''})" if total > 1 else ""
        partes.append(c("› ", "verde") + c(primeira[:60], "verde") + c(extra, "cinza"))
    if "retorna" in linha:
        partes.append(c(f"retorna {linha['retorna']}", "cinza"))
    return partes


def desenhar(r, mostrar_tudo=False):
    with open(r["arquivo"], encoding="utf-8") as fh:
        codigo = fh.read().splitlines()
    largura_tela = shutil.get_terminal_size((140, 40)).columns
    larg_cod = min(max((len(x) for x in codigo), default=10) + 2, 56)
    erro = r.get("erro")
    limite = r.get("limite")
    nome = os.path.basename(r["arquivo"])
    cab = [c("True Coral", "vermelho", "negrito"), nome, f"Python {r['python']}"]
    if "tempo_ms" in r:
        cab.append(f"{r['tempo_ms']:.0f} ms" if r["tempo_ms"] >= 1 else "<1 ms")
    if limite:
        cab.append(c(f"⏱ parou no limite de {limite['motivo']} na linha {limite['linha']}", "amarelo"))
    if erro:
        cab.append(c(f"✕ {erro['tipo']} na linha {erro['linha']}", "vermelho"))
    saida = [c(" · ", "cinza").join(cab), ""]
    linhas = r["linhas"]
    for i, texto in enumerate(codigo, 1):
        cod = texto if len(texto) <= larg_cod - 2 else texto[: larg_cod - 3] + "…"
        num = c(f"{i:>3}  ", "cinza")
        info = linhas.get(str(i))
        pedacos = []
        if erro and erro.get("linha") == i:
            pedacos.append(c(f"✕ {erro['tipo']}", "vermelho", "negrito"))
        elif info:
            if info.get("vezes") == 0 and not (erro and i > (erro.get("linha") or 0)):
                pedacos.append(c("· não rodou", "cinza"))
            else:
                pedacos += chips(info, i)
        linha_txt = num + cod.ljust(larg_cod) + (c("   ", "cinza").join(pedacos))
        saida.append(linha_txt)
        if info and info.get("detalhe"):
            saida.append(" " * (5 + larg_cod) + c("↳ " + info["detalhe"], "cinza"))
        if erro and erro.get("linha") == i:
            if erro.get("explica"):
                saida.append(" " * 5 + c("✕ ", "vermelho") + c(erro["explica"], "vermelho"))
            saida.append(" " * 7 + c(f"{erro['tipo']}: {erro['mensagem']}", "cinza"))
    if erro and not erro.get("linha"):
        saida += ["", c(f"✕ {erro['tipo']}: {erro['mensagem']}", "vermelho")]
    saida += ["", c("= o que a linha guardou   › o que o print escreveu   ↻ laço   ! fato que merece atenção   "
                    "✕ erro   · não rodou", "cinza")]
    return "\n".join(saida)


AJUDA = f"""{c('coral', 'vermelho', 'negrito')} {__version__} — o True Coral: o que cada linha do seu código fez

uso: coral arquivo.py [opções]

opções:
  --python CAMINHO   roda com este Python (padrão: o .venv da pasta, o ambiente ativo ou o python3)
  --tempo SEGUNDOS   limite de tempo; um laço infinito para aqui (padrão: 10)
  --json             o resultado cru do motor, para outras ferramentas (a extensão do VS Code)
  -h, --help         esta ajuda
  -V, --version      a versão

o código RODA de verdade: se ele apaga ou grava arquivo, isso acontece. O input() fica desligado.
"""


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] in ("-h", "--help"):
        print(AJUDA)
        return 0
    if args[0] in ("-V", "--version"):
        print(f"coral {__version__}")
        return 0
    arquivo, python, tempo, como_json = None, None, 10.0, False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--python":
            python, i = args[i + 1], i + 2
        elif a == "--tempo":
            tempo, i = float(args[i + 1]), i + 2
        elif a == "--json":
            como_json, i = True, i + 1
        elif a.startswith("-"):
            print(f"coral: opção desconhecida: {a} (veja coral -h)", file=sys.stderr)
            return 2
        else:
            arquivo, i = a, i + 1
    if not arquivo or not os.path.isfile(arquivo):
        print(f"coral: arquivo não encontrado: {arquivo}", file=sys.stderr)
        return 2
    py = achar_python(arquivo, python)
    try:
        r = rodar_motor(arquivo, py, tempo)
    except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        print(f"coral: {e}", file=sys.stderr)
        return 1
    if como_json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(desenhar(r))
    return 0
