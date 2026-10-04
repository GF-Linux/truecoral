"""O motor do True Coral: roda um arquivo Python e registra, linha a linha, o que aconteceu.

    python motor.py arquivo.py [--saida resultado.json] [--tempo 10] [--passos 5000000]

Só biblioteca padrão: roda com qualquer Python 3.9+, o mesmo que vai rodar o seu código.

O que ele registra, por linha:
  - quantas vezes a linha rodou (e quais nunca rodaram)
  - o que cada atribuição guardou — e, se a linha rodou várias vezes, a evolução do valor
  - nos laços: quantas voltas, e por onde saiu (fim, condição falsa ou break)
  - nos if/while: quantas vezes a condição deu True e quantas deu False
  - o que o print escreveu, separado do que a linha devolveu
  - o erro, se houver: o tipo, a mensagem original e uma explicação em português

Descreve, não julga: o motor conta e mostra; quem decide se está certo é quem escreveu.
O código roda de verdade — se ele apaga um arquivo, apaga. Por isso há limite de tempo e de
passos, e o input() é desligado (não há teclado).
"""
import ast
import builtins
import json
import os
import sys
import time

VERSAO_FORMATO = 1
HISTORICO = 4            # quantos valores do começo guardar; o último sempre é guardado
SAIDA_MAX = 2000         # caracteres de print guardados por linha
REDUCOES = {"mean", "sum", "median", "std", "var", "min", "max", "count", "prod"}

EXPLICA = {
    "SyntaxError": "o Python não conseguiu ler esta linha como código",
    "IndentationError": "o recuo (indentação) desta linha não combina com o bloco em que ela está",
    "TabError": "a linha mistura tab e espaço no recuo",
    "NameError": "este nome não existe neste ponto do código: ainda não foi criado, ou está escrito diferente",
    "UnboundLocalError": "a variável é usada antes de receber um valor dentro da função",
    "TypeError": "a operação não aceita este tipo de valor",
    "ValueError": "o tipo está certo, mas este valor não serve para a operação",
    "ZeroDivisionError": "divisão por zero",
    "KeyError": "esta chave não existe (num dicionário, ou uma coluna que o DataFrame não tem)",
    "IndexError": "a posição pedida está fora do tamanho da lista",
    "AttributeError": "este objeto não tem este atributo ou método",
    "ModuleNotFoundError": "este módulo não está instalado neste Python",
    "ImportError": "o módulo existe, mas não tem o que foi pedido",
    "FileNotFoundError": "não existe arquivo neste caminho — confira onde você está (pwd) e o que há ali (ls)",
    "RecursionError": "a função chamou a si mesma vezes demais",
    "AssertionError": "um assert deu False",
}


class Parada(BaseException):
    """O limite de tempo ou de passos chegou: o laço pode ser infinito."""


# ── 1. ler o código antes de rodar ──────────────────────────────────────────

def _nomes(alvo):
    if isinstance(alvo, ast.Name):
        return [alvo.id]
    if isinstance(alvo, (ast.Tuple, ast.List)):
        return [n for e in alvo.elts for n in _nomes(e)]
    if isinstance(alvo, ast.Starred):
        return _nomes(alvo.value)
    return []


class Mapa(ast.NodeVisitor):
    """O que cada linha é: atribuição, laço, condição, break, print, redução."""

    def __init__(self, fonte):
        self.fonte = fonte
        self.alvos, self.lacos, self.condicoes, self.breaks = {}, {}, {}, {}
        self.prints, self.reducoes, self.inicios = set(), {}, set()
        self._laco_atual = []

    def _bloco(self, corpo):
        return corpo[0].lineno, corpo[-1].end_lineno

    def generic_visit(self, no):
        if isinstance(no, ast.stmt):
            self.inicios.add(no.lineno)
        super().generic_visit(no)

    def visit_Assign(self, no):
        for alvo in no.targets:
            self.alvos.setdefault(no.lineno, []).extend(_nomes(alvo))
        self._reducao(no)
        self.generic_visit(no)

    def visit_AnnAssign(self, no):
        if no.value is not None:
            self.alvos.setdefault(no.lineno, []).extend(_nomes(no.target))
            self._reducao(no)
        self.generic_visit(no)

    def visit_AugAssign(self, no):
        self.alvos.setdefault(no.lineno, []).extend(_nomes(no.target))
        self.generic_visit(no)

    def _reducao(self, no):
        v = no.value
        if (isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr in REDUCOES
                and isinstance(v.func.value, (ast.Name, ast.Subscript))):
            fonte = ast.get_source_segment(self.fonte, v.func.value)
            if fonte and "(" not in fonte:           # só nomes e colunas: ler de novo é seguro
                self.reducoes[no.lineno] = (fonte, v.func.attr)

    def _laco(self, no, tipo):
        ini, fim = self._bloco(no.body)
        self.lacos[no.lineno] = {"tipo": tipo, "corpo": [ini, fim]}
        self._laco_atual.append(no.lineno)
        for filho in no.body:
            self.visit(filho)
        self._laco_atual.pop()
        for filho in no.orelse:
            self.visit(filho)

    def visit_For(self, no):
        self.inicios.add(no.lineno)
        self.alvos.setdefault(no.lineno, []).extend(_nomes(no.target))
        self.visit(no.iter)
        self._laco(no, "for")

    visit_AsyncFor = visit_For

    def visit_While(self, no):
        self.inicios.add(no.lineno)
        self.condicoes[no.lineno] = list(self._bloco(no.body))
        self._laco(no, "while")

    def visit_If(self, no):
        self.inicios.add(no.lineno)
        ini, fim = self._bloco(no.body)
        if ini != no.lineno:                         # if x: y  numa linha só não dá para separar
            self.condicoes[no.lineno] = [ini, fim]
        self.generic_visit(no)

    def visit_Break(self, no):
        self.inicios.add(no.lineno)
        if self._laco_atual:
            self.breaks[no.lineno] = self._laco_atual[-1]

    def visit_FunctionDef(self, no):
        self.inicios.add(no.lineno)
        guardado, self._laco_atual = self._laco_atual, []
        self.generic_visit(no)
        self._laco_atual = guardado

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Expr(self, no):
        v = no.value
        if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "print":
            self.prints.add(no.lineno)
        self.generic_visit(no)


# ── 2. resumir um valor em poucas palavras ──────────────────────────────────

def _curto(texto, n=60):
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= n else texto[: n - 1] + "…"


def resumir(v):
    """(texto, tipo, aviso). O aviso é um fato que merece atenção — vazios, NaN —, nunca um julgamento."""
    tipo = type(v).__name__
    pd = sys.modules.get("pandas")
    try:
        if pd is not None and isinstance(v, pd.DataFrame):
            vazios = v.isna().sum()
            com = [str(c) for c, n in vazios.items() if n]
            aviso = (f"{int(vazios.sum())} vazio{'s' if vazios.sum() != 1 else ''} (NaN) em {', '.join(com[:4])}"
                     if com else None)
            return f"{v.shape[0]} × {v.shape[1]}", "DataFrame", aviso
        if pd is not None and isinstance(v, pd.Series):
            vaz = int(v.isna().sum())
            nome = f" «{v.name}»" if v.name is not None else ""
            return f"{len(v)} valores{nome}", f"Series {v.dtype}", (f"{vaz} vazio{'s' if vaz != 1 else ''} (NaN)"
                                                                   if vaz else None)
        if isinstance(v, (list, tuple, set, frozenset, dict, str)):
            return _curto(repr(v)), f"{tipo} · {len(v)}", None
        if isinstance(v, float) and v != v:
            return "nan", tipo, "NaN: um número que não existe"
        if hasattr(v, "dtype") and getattr(v, "shape", None) == ():           # número do numpy
            texto = _curto(repr(v.item()) if hasattr(v, "item") else repr(v))
            aviso = "NaN: um número que não existe" if texto == "nan" else None
            return texto, tipo, aviso
        if isinstance(v, type(sys)):
            return v.__name__, "módulo", None
        if callable(v) and hasattr(v, "__name__"):
            return v.__name__ + "()", "função", None
        return _curto(repr(v)), tipo, None
    except Exception:
        return "?", tipo, None


# ── 3. rodar e registrar ────────────────────────────────────────────────────

class Registro:
    def __init__(self, mapa, limite_tempo, limite_passos):
        self.mapa = mapa
        self.linhas = {}
        self.estados = {}
        self.atual = None
        self.passos = 0
        self.inicio = time.perf_counter()
        self.limite_tempo, self.limite_passos = limite_tempo, limite_passos
        self.saidas_laco = {}
        self.limite = None

    def _linha(self, n):
        return self.linhas.setdefault(n, {"vezes": 0})

    def _guardar_valor(self, n, nome, v):
        texto, tipo, aviso = resumir(v)
        reg = self._linha(n).setdefault("valores", {}).setdefault(nome, {"historico": [], "total": 0})
        reg["total"] += 1
        reg["tipo"] = tipo
        if aviso:
            reg["aviso"] = aviso
        h = reg["historico"]
        if len(h) < HISTORICO:
            h.append(texto)
        reg["ultimo"] = texto

    def _finalizar(self, quadro, n, proxima):
        mapa = self.mapa
        laco = mapa.lacos.get(n)
        comecou_volta = laco is None or laco["tipo"] != "for" or (
            proxima is not None and laco["corpo"][0] <= proxima <= laco["corpo"][1])
        for nome in (mapa.alvos.get(n, ()) if comecou_volta else ()):
            if nome in quadro.f_locals:
                self._guardar_valor(n, nome, quadro.f_locals[nome])
            elif nome in quadro.f_globals:
                self._guardar_valor(n, nome, quadro.f_globals[nome])
        if n in mapa.reducoes and "detalhe" not in self._linha(n):
            fonte, metodo = mapa.reducoes[n]
            try:
                serie = eval(fonte, quadro.f_globals, dict(quadro.f_locals))
                total, uteis = len(serie), int(serie.notna().sum())
                detalhe = f"{metodo}() usou {uteis} de {total} valores"
                if uteis < total:
                    detalhe += f" — ignorou {total - uteis} vazio{'s' if total - uteis != 1 else ''} (NaN)"
                self._linha(n)["detalhe"] = detalhe
            except Exception:
                pass

    def _decidir(self, cond, verdadeiro):
        c = self._linha(cond).setdefault("condicao", {"True": 0, "False": 0})
        c["True" if verdadeiro else "False"] += 1

    def rastrear(self, quadro, evento, arg):
        if quadro.f_code.co_filename != self.arquivo:
            return None
        self.estados[quadro] = {"pendente": None, "condicao": None}
        return self.local

    def local(self, quadro, evento, arg):
        self.passos += 1
        if self.passos % 20000 == 0:
            if self.passos > self.limite_passos or time.perf_counter() - self.inicio > self.limite_tempo:
                motivo = "passos" if self.passos > self.limite_passos else "tempo"
                self.limite = {"motivo": motivo, "linha": quadro.f_lineno, "passos": self.passos}
                raise Parada()
        est = self.estados.get(quadro)
        if est is None:
            est = self.estados[quadro] = {"pendente": None, "condicao": None}
        if evento == "line":
            n = quadro.f_lineno
            if est["pendente"] is not None:
                self._finalizar(quadro, est["pendente"], n)
                if est["pendente"] in self.mapa.condicoes:
                    est["condicao"] = est["pendente"]
            if est["condicao"] is not None:
                ini, fim = self.mapa.condicoes[est["condicao"]]
                self._decidir(est["condicao"], ini <= n <= fim)
                est["condicao"] = None
            self._linha(n)["vezes"] += 1
            if n in self.mapa.breaks:
                self.saidas_laco[self.mapa.breaks[n]] = n
            est["pendente"] = n
            self.atual = n
        elif evento == "return":
            if est["pendente"] is not None:
                self._finalizar(quadro, est["pendente"], None)
                if est["pendente"] in self.mapa.condicoes:
                    self._decidir(est["pendente"], False)
            self.estados.pop(quadro, None)
        return self.local


class Captura:
    """O stdout do código: cada pedaço de texto vai para a linha que o escreveu."""

    def __init__(self, registro):
        self.registro = registro

    def write(self, texto):
        n = self.registro.atual
        if n is not None and texto:
            linha = self.registro._linha(n)
            atual = linha.get("saida", "")
            if len(atual) < SAIDA_MAX:                # o texto guardado tem teto; a contagem, não
                linha["saida"] = (atual + texto)[:SAIDA_MAX]
            linha["linhas_saida"] = linha.get("linhas_saida", 0) + texto.count("\n")
        return len(texto)

    def flush(self):
        pass

    def isatty(self):
        return False


def _sem_teclado(*_args, **_kw):
    raise RuntimeError("input() não funciona no True Coral: não há teclado durante a análise")


def analisar(arquivo, limite_tempo=10.0, limite_passos=5_000_000):
    arquivo = os.path.abspath(arquivo)
    with open(arquivo, encoding="utf-8") as fh:
        fonte = fh.read()
    resultado = {"formato": VERSAO_FORMATO, "arquivo": arquivo,
                 "python": "%d.%d.%d" % sys.version_info[:3], "linhas": {}, "erro": None, "limite": None}
    try:
        arvore = ast.parse(fonte, filename=arquivo)
        codigo = compile(arvore, arquivo, "exec")
    except SyntaxError as e:
        tipo = type(e).__name__
        resultado["erro"] = {"linha": e.lineno, "tipo": tipo, "mensagem": e.msg,
                             "explica": EXPLICA.get(tipo, ""), "coluna": e.offset}
        return resultado

    mapa = Mapa(fonte)
    mapa.visit(arvore)
    reg = Registro(mapa, limite_tempo, limite_passos)
    reg.arquivo = arquivo
    globais = {"__name__": "__main__", "__file__": arquivo, "__builtins__": builtins}
    stdout, stderr, entrada, argv = sys.stdout, sys.stderr, builtins.input, sys.argv
    sys.path.insert(0, os.path.dirname(arquivo))
    sys.argv = [arquivo]
    sys.stdout = Captura(reg)
    builtins.input = _sem_teclado
    inicio = time.perf_counter()
    try:
        sys.settrace(reg.rastrear)
        exec(codigo, globais)
    except Parada:
        resultado["limite"] = reg.limite
    except SystemExit as e:
        resultado["saiu"] = {"linha": reg.atual, "codigo": e.code}
    except BaseException as e:                       # o erro do código é um resultado, não uma falha
        linha = reg.atual
        tb = e.__traceback__
        while tb is not None:
            if tb.tb_frame.f_code.co_filename == arquivo:
                linha = tb.tb_lineno
            tb = tb.tb_next
        tipo = type(e).__name__
        resultado["erro"] = {"linha": linha, "tipo": tipo, "mensagem": str(e), "explica": EXPLICA.get(tipo, "")}
    finally:
        sys.settrace(None)
        sys.stdout, sys.stderr, builtins.input, sys.argv = stdout, stderr, entrada, argv
    resultado["tempo_ms"] = round((time.perf_counter() - inicio) * 1000, 1)
    resultado["passos"] = reg.passos

    # os laços: voltas = quantas vezes a primeira linha do corpo rodou
    for n, laco in mapa.lacos.items():
        if n not in reg.linhas:
            continue
        voltas = reg.linhas.get(laco["corpo"][0], {}).get("vezes", 0)
        if n in reg.saidas_laco:
            saida = {"como": "break", "linha": reg.saidas_laco[n]}
        elif resultado["limite"] and n <= resultado["limite"]["linha"] <= laco["corpo"][1]:
            saida = {"como": "limite"}
        elif laco["tipo"] == "while":
            saida = {"como": "condição falsa"}
        else:
            saida = {"como": "fim"}
        reg.linhas[n]["laco"] = {"tipo": laco["tipo"], "voltas": voltas, "saida": saida}
    for n in mapa.prints:
        if n in reg.linhas:
            reg.linhas[n]["retorna"] = "None"
    for n in mapa.inicios:
        if n not in reg.linhas:
            reg.linhas[n] = {"vezes": 0}
    resultado["linhas"] = {str(k): v for k, v in sorted(reg.linhas.items())}
    return resultado


def main(args):
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    arquivo, saida, tempo, passos = args[0], None, 10.0, 5_000_000
    i = 1
    while i < len(args):
        if args[i] == "--saida":
            saida, i = args[i + 1], i + 2
        elif args[i] == "--tempo":
            tempo, i = float(args[i + 1]), i + 2
        elif args[i] == "--passos":
            passos, i = int(args[i + 1]), i + 2
        else:
            print(f"motor: argumento desconhecido: {args[i]}", file=sys.stderr)
            return 2
    resultado = analisar(arquivo, tempo, passos)
    texto = json.dumps(resultado, ensure_ascii=False, indent=1)
    if saida:
        with open(saida, "w", encoding="utf-8") as fh:
            fh.write(texto)
    else:
        sys.stdout.write(texto + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
