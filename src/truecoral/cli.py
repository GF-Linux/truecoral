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


# ── o desenho no terminal ──────────────────────────────────────────────────
# O texto de cada chip vem pronto do motor; aqui só entra a cor.

COR_DO_TIPO = {"valor": "azul", "saida": "verde", "laco": "lilas", "condicao": "lilas", "aviso": "amarelo",
               "erro": "vermelho", "naorodou": "cinza", "retorna": "cinza"}


def desenhar(r):
    with open(r["arquivo"], encoding="utf-8") as fh:
        codigo = fh.read().splitlines()
    larg_cod = min(max((len(x) for x in codigo), default=10) + 2, 56)
    erro, limite = r.get("erro"), r.get("limite")
    cab = [c("True Coral", "vermelho", "negrito"), os.path.basename(r["arquivo"]), f"Python {r['python']}"]
    if "tempo_ms" in r:
        cab.append(f"{r['tempo_ms']:.0f} ms" if r["tempo_ms"] >= 1 else "<1 ms")
    if limite:
        cab.append(c(f"⏱ parou no limite de {limite['motivo']} na linha {limite['linha']}", "amarelo"))
    if erro:
        cab.append(c(f"✕ {erro['tipo']} na linha {erro['linha']}", "vermelho"))
    saida = [c(" · ", "cinza").join(cab), ""]
    for i, texto in enumerate(codigo, 1):
        cod = texto if len(texto) <= larg_cod - 2 else texto[: larg_cod - 3] + "…"
        info = r["linhas"].get(str(i), {})
        pedacos = [c(ch["texto"], COR_DO_TIPO.get(ch["tipo"], "cinza"), *(("negrito",) if ch["tipo"] in ("erro", "laco")
                                                                       else ()))
                   for ch in info.get("chips", [])]
        saida.append(c(f"{i:>3}  ", "cinza") + cod.ljust(larg_cod) + "   ".join(pedacos))
        for d in info.get("detalhes", []):
            if erro and erro.get("linha") == i:
                saida.append(" " * 5 + c(d, "vermelho" if d == erro.get("explica") else "cinza"))
            elif "\n" not in d and not d.startswith(tuple(f"{k}:" for k in info.get("valores", {}))):
                saida.append(" " * (5 + larg_cod) + c("↳ " + d, "cinza"))
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
