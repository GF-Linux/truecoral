// True Coral — a extensão só desenha. Quem lê e quem roda são dois programas em Python (biblioteca padrão).
//
// A cada tecla: a leitura.py lê o texto, ainda sem salvar, e diz o que cada linha faz ("— ...") e o
// erro de escrita traduzido ("✕ ..."). Não roda nada do seu código.
// Ao salvar: o motor.py roda o arquivo com o Python do seu projeto e põe ao lado de cada linha o que
// ela produziu (= › ↩ ↻ ...). Ao passar o mouse, os detalhes. Erro vira também sublinhado vermelho (e
// entra no painel de Problemas). Ao editar, os valores somem: eles valem para o arquivo salvo, e as
// linhas mudam de lugar enquanto você digita. A descrição fica, porque é refeita a cada tecla.

const vscode = require("vscode");
const cp = require("child_process");
const fs = require("fs");
const path = require("path");

// a ordem aqui é a ordem dos chips na linha
const TIPOS = {
  chamada:  { cor: "#d4b4f0", fundo: "rgba(190,150,230,0.10)" },
  laco:     { cor: "#d4b4f0", fundo: "rgba(190,150,230,0.14)" },
  condicao: { cor: "#d4b4f0", fundo: "rgba(190,150,230,0.10)" },
  valor:    { cor: "#8ec5f5", fundo: "rgba(74,163,239,0.14)" },
  aviso:    { cor: "#f2c56b", fundo: "rgba(240,180,60,0.14)" },
  excecao:  { cor: "#f5a86b", fundo: "rgba(240,138,60,0.14)" },
  saida:    { cor: "#8fdcaa", fundo: "rgba(110,200,140,0.14)" },
  retorna:  { cor: "#7d8592", fundo: undefined },
  erro:     { cor: "#f08a80", fundo: "rgba(235,100,90,0.16)" },
  naorodou: { cor: "#6b7280", fundo: undefined, italico: true },
  escrita:  { cor: "#f08a80", fundo: "rgba(235,100,90,0.16)" },          // da leitura: a cada tecla
  descricao:{ cor: "#7d8592", fundo: undefined, italico: true },
};
const DA_LEITURA = new Set(["escrita", "descricao"]);

let decoracoes = {};
let diagnosticos;
let barra;
let processos = new Map();     // arquivo → processo do motor em andamento
let leituras = new Map();      // arquivo → { processo, temporizador }
let ultimaLeitura = new Map(); // arquivo → a última leitura desenhada (redesenhada depois dos valores)
let pythons = new Map();       // arquivo → o Python achado (a leitura roda a cada tecla: achar uma vez só)

// O VS Code põe na linha os textos de tipos diferentes na ordem do número interno de cada tipo, comparado
// como TEXTO: o tipo 12 vem antes do 4. Com todos os números do mesmo tamanho, a ordem é a de criação —
// a de TIPOS: os valores primeiro, a descrição por último.
function numeroDo(tipo) {
  const m = /(\d+)$/.exec(tipo.key || "");
  return m ? parseInt(m[1], 10) : 0;
}

function alinharNumeros(quantos) {
  const sondas = [vscode.window.createTextEditorDecorationType({})];
  let k = numeroDo(sondas[0]);
  while (String(k + 1).length !== String(k + quantos).length && sondas.length < 2000) {
    const s = vscode.window.createTextEditorDecorationType({});
    sondas.push(s);
    k = numeroDo(s);
  }
  for (const s of sondas) s.dispose();
}

function criarDecoracoes() {
  alinharNumeros(Object.keys(TIPOS).length);
  for (const [tipo, d] of Object.entries(TIPOS)) {
    decoracoes[tipo] = vscode.window.createTextEditorDecorationType({
      after: {
        margin: "0 0 0 1.4em",
        color: d.cor,
        backgroundColor: d.fundo,
        fontStyle: d.italico ? "italic" : "normal",
      },
      rangeBehavior: vscode.DecorationRangeBehavior.ClosedClosed,
    });
  }
}

async function acharPython(documento) {
  const cfg = vscode.workspace.getConfiguration("truecoral", documento.uri);
  if (cfg.get("pythonPath")) return cfg.get("pythonPath");
  try {   // o ambiente escolhido na extensão Python da Microsoft, se ela estiver lá
    const ext = vscode.extensions.getExtension("ms-python.python");
    if (ext) {
      const api = ext.isActive ? ext.exports : await ext.activate();
      const env = await api.environments.getActiveEnvironmentPath(documento.uri);
      if (env && env.path && fs.existsSync(env.path)) return env.path;
    }
  } catch (e) { /* segue para o próximo jeito */ }
  const pastas = [path.dirname(documento.uri.fsPath)];
  const ws = vscode.workspace.getWorkspaceFolder(documento.uri);
  if (ws) pastas.push(ws.uri.fsPath);
  for (const p of pastas) {
    for (const nome of [".venv", "venv", "env"]) {
      const py = path.join(p, nome, "bin", "python");
      if (fs.existsSync(path.join(p, nome, "pyvenv.cfg")) && fs.existsSync(py)) return py;
    }
  }
  return "python3";
}

function limpar(editor, tambemLeitura = true) {
  if (!editor) return;
  for (const [tipo, d] of Object.entries(decoracoes)) {
    if (tambemLeitura || !DA_LEITURA.has(tipo)) editor.setDecorations(d, []);
  }
  diagnosticos.delete(editor.document.uri);
}

async function pythonDe(documento) {
  const chave = documento.uri.fsPath;
  if (!pythons.has(chave)) pythons.set(chave, await acharPython(documento));
  return pythons.get(chave);
}

// ── a leitura: a cada tecla, sem rodar nada ─────────────────────────────────
function desenharLeitura(editor, r) {
  const doc = editor.document;
  const porTipo = { escrita: [], descricao: [] };
  const fimDa = (n) => doc.lineAt(n).range.end;
  for (const [chave, linha] of Object.entries(r.linhas || {})) {
    const n = parseInt(chave, 10) - 1;
    if (n < 0 || n >= doc.lineCount || !linha.descricao) continue;
    porTipo.descricao.push({ range: new vscode.Range(fimDa(n), fimDa(n)),
      renderOptions: { after: { contentText: " — " + linha.descricao + " " } } });
  }
  const e = r.erro;
  if (e && e.linha) {
    const n = Math.min(Math.max(e.linha - 1, 0), doc.lineCount - 1);
    porTipo.escrita.push({ range: new vscode.Range(fimDa(n), fimDa(n)),
      hoverMessage: new vscode.MarkdownString(`${e.texto}\n\n*o Python diz:* \`${e.original}\``),
      renderOptions: { after: { contentText: " ✕ " + e.texto + " " } } });
  }
  for (const [tipo, lista] of Object.entries(porTipo)) editor.setDecorations(decoracoes[tipo], lista);
}

function ler(documento, espera) {
  if (!documento || documento.languageId !== "python" || documento.uri.scheme !== "file") return;
  if (!vscode.workspace.getConfiguration("truecoral", documento.uri).get("descrever")) return;
  const arquivo = documento.uri.fsPath;
  const antes = leituras.get(arquivo);
  if (antes) { clearTimeout(antes.temporizador); if (antes.processo) antes.processo.kill(); }
  const estado = { processo: null, temporizador: null };
  leituras.set(arquivo, estado);
  estado.temporizador = setTimeout(async () => {
    const versao = documento.version;
    const python = await pythonDe(documento);
    if (leituras.get(arquivo) !== estado) return;
    const filho = cp.execFile(python, [path.join(__dirname, "leitura.py"), "-"],
      { timeout: 15000, maxBuffer: 16 * 1024 * 1024 }, (falha, stdout) => {
        if (leituras.get(arquivo) !== estado || falha || !stdout) return;
        if (documento.version !== versao) return;          // o texto mudou enquanto lia: a próxima leitura vem
        const editor = vscode.window.visibleTextEditors.find((ed) => ed.document === documento);
        if (!editor) return;
        try {
          const r = JSON.parse(stdout);
          ultimaLeitura.set(arquivo, r);
          desenharLeitura(editor, r);
        } catch (e) { /* uma leitura ruim não apaga a anterior */ }
      });
    filho.stdin.end(documento.getText());
    estado.processo = filho;
  }, espera);
}

function desenhar(editor, r) {
  const porTipo = Object.fromEntries(Object.keys(TIPOS).map((t) => [t, []]));
  const doc = editor.document;
  for (const [chave, linha] of Object.entries(r.linhas || {})) {
    const n = parseInt(chave, 10) - 1;
    if (n < 0 || n >= doc.lineCount) continue;
    const fim = doc.lineAt(n).range.end;
    const detalhes = (linha.detalhes || []).filter(Boolean);
    let primeiro = true;
    for (const chip of linha.chips || []) {
      if (chip.tipo === "erro" && r.erro && r.erro.escrita &&
          vscode.workspace.getConfiguration("truecoral", doc.uri).get("descrever")) continue;
      const hover = primeiro && detalhes.length
        ? new vscode.MarkdownString(detalhes.map((d) => d.includes("\n") ? "```\n" + d + "\n```" : d).join("\n\n"))
        : undefined;
      primeiro = false;
      (porTipo[chip.tipo] || porTipo.valor).push({
        range: new vscode.Range(fim, fim),
        hoverMessage: hover,
        renderOptions: { after: { contentText: " " + chip.texto + " " } },
      });
    }
  }
  for (const [tipo, lista] of Object.entries(porTipo)) {
    if (!DA_LEITURA.has(tipo)) editor.setDecorations(decoracoes[tipo], lista);   // a leitura é da outra camada
  }
  // o VS Code põe na linha os textos na ordem em que foram desenhados: a descrição, desenhada de novo
  // agora, fica sempre depois dos valores — código, valores, descrição, como no coral do terminal
  const leitura = ultimaLeitura.get(doc.uri.fsPath);
  if (leitura && vscode.workspace.getConfiguration("truecoral", doc.uri).get("descrever")) desenharLeitura(editor, leitura);

  const erro = r.erro;
  if (erro && erro.linha) {
    const n = Math.min(Math.max(erro.linha - 1, 0), doc.lineCount - 1);
    const linha = doc.lineAt(n);
    const d = new vscode.Diagnostic(
      new vscode.Range(linha.firstNonWhitespaceCharacterIndex === undefined ? linha.range.start
        : new vscode.Position(n, linha.firstNonWhitespaceCharacterIndex), linha.range.end),
      `${erro.explica ? erro.explica + "\n" : ""}${erro.tipo}: ${erro.mensagem}`,
      vscode.DiagnosticSeverity.Error);
    d.source = "True Coral";
    diagnosticos.set(doc.uri, [d]);
  } else {
    diagnosticos.delete(doc.uri);
  }

  let texto = `$(eye) True Coral · ${r.tempo_ms !== undefined ? (r.tempo_ms < 1 ? "<1" : Math.round(r.tempo_ms)) + " ms" : ""}`;
  if (erro) texto = `$(error) True Coral · ${erro.tipo} na linha ${erro.linha}`;
  else if (r.limite) texto = `$(watch) True Coral · parou no limite na linha ${r.limite.linha}`;
  barra.text = texto;
  barra.tooltip = `Python ${r.python} · clique para analisar de novo`;
  barra.show();
}

async function analisar(documento) {
  if (!documento || documento.languageId !== "python" || documento.uri.scheme !== "file") return;
  const editor = vscode.window.visibleTextEditors.find((e) => e.document === documento);
  if (!editor) return;
  const arquivo = documento.uri.fsPath;
  const anterior = processos.get(arquivo);
  if (anterior) anterior.kill();

  const cfg = vscode.workspace.getConfiguration("truecoral", documento.uri);
  const tempo = cfg.get("tempo") || 10;
  const python = await pythonDe(documento);
  const motor = path.join(__dirname, "motor.py");
  const ws = vscode.workspace.getWorkspaceFolder(documento.uri);
  barra.text = "$(sync~spin) True Coral";
  barra.show();

  const filho = cp.execFile(python, [motor, arquivo, "--tempo", String(tempo)],
    { cwd: ws ? ws.uri.fsPath : path.dirname(arquivo), timeout: (tempo + 30) * 1000, maxBuffer: 64 * 1024 * 1024 },
    (falha, stdout, stderr) => {
      if (processos.get(arquivo) !== filho) return;          // uma análise mais nova já começou
      processos.delete(arquivo);
      if (falha && !stdout) {
        barra.text = "$(warning) True Coral · o motor não rodou";
        barra.tooltip = (stderr || String(falha)).slice(0, 2000);
        return;
      }
      try {
        desenhar(editor, JSON.parse(stdout));
      } catch (e) {
        barra.text = "$(warning) True Coral · resposta inválida do motor";
        barra.tooltip = String(e);
      }
    });
  processos.set(arquivo, filho);
}

function activate(contexto) {
  criarDecoracoes();
  diagnosticos = vscode.languages.createDiagnosticCollection("truecoral");
  barra = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 50);
  barra.command = "truecoral.analisar";

  contexto.subscriptions.push(
    diagnosticos, barra,
    ...Object.values(decoracoes),
    vscode.commands.registerCommand("truecoral.analisar", async () => {
      const ed = vscode.window.activeTextEditor;
      if (!ed) return;
      if (ed.document.isDirty) await ed.document.save();     // o motor lê o arquivo salvo
      else analisar(ed.document);
    }),
    vscode.commands.registerCommand("truecoral.limpar", () => limpar(vscode.window.activeTextEditor)),
    vscode.commands.registerCommand("truecoral.alternarDescricao", async () => {
      const cfg = vscode.workspace.getConfiguration("truecoral");
      const novo = !cfg.get("descrever");
      await cfg.update("descrever", novo, vscode.ConfigurationTarget.Global);
      const ed = vscode.window.activeTextEditor;
      if (novo && ed) ler(ed.document, 0);
      else if (ed) { ed.setDecorations(decoracoes.descricao, []); ed.setDecorations(decoracoes.escrita, []); }
      vscode.window.showInformationMessage(`True Coral, descrição das linhas: ${novo ? "ligada" : "desligada"}`);
    }),
    vscode.commands.registerCommand("truecoral.alternar", async () => {
      const cfg = vscode.workspace.getConfiguration("truecoral");
      const novo = !cfg.get("aoSalvar");
      await cfg.update("aoSalvar", novo, vscode.ConfigurationTarget.Global);
      vscode.window.showInformationMessage(`True Coral ao salvar: ${novo ? "ligado" : "desligado"}`);
    }),
    vscode.workspace.onDidSaveTextDocument((doc) => {
      if (vscode.workspace.getConfiguration("truecoral", doc.uri).get("aoSalvar")) analisar(doc);
    }),
    vscode.workspace.onDidChangeTextDocument((ev) => {        // os valores valem para o salvo; a leitura é refeita
      if (ev.contentChanges.length === 0) return;
      const ed = vscode.window.visibleTextEditors.find((e) => e.document === ev.document);
      if (ed) limpar(ed, false);
      ler(ev.document, 250);
    }),
    vscode.window.onDidChangeActiveTextEditor((ed) => { if (ed) ler(ed.document, 0); }),
    vscode.workspace.onDidOpenTextDocument((doc) => ler(doc, 0)),
    vscode.workspace.onDidCloseTextDocument((doc) => {
      pythons.delete(doc.uri.fsPath); leituras.delete(doc.uri.fsPath); ultimaLeitura.delete(doc.uri.fsPath);
    }),
    vscode.workspace.onDidChangeConfiguration((ev) => { if (ev.affectsConfiguration("truecoral.pythonPath")) pythons.clear(); }),
  );
  for (const ed of vscode.window.visibleTextEditors) ler(ed.document, 0);
}

function deactivate() {
  for (const p of processos.values()) p.kill();
  for (const l of leituras.values()) { clearTimeout(l.temporizador); if (l.processo) l.processo.kill(); }
}

module.exports = { activate, deactivate };
