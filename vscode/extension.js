// True Coral — a extensão só desenha. Quem lê e quem roda são dois programas em Python (biblioteca padrão).
//
// A cada tecla: a leitura.py lê o texto, ainda sem salvar, e diz o que cada linha faz ("# ...", numa
// coluna alinhada, como um comentário) e o erro de escrita traduzido ("✕ ..."). Não roda nada do seu código.
// Ao salvar: o motor.py roda o arquivo com o Python do seu projeto e põe ao lado de cada linha o que
// ela produziu (= › ↩ ↻ ...). Ao passar o mouse, os detalhes. Erro vira também sublinhado vermelho (e
// entra no painel de Problemas). Ao editar, os valores somem: eles valem para o arquivo salvo, e as
// linhas mudam de lugar enquanto você digita. A descrição fica, porque é refeita a cada tecla.
// Também ao salvar: as setas do fluxo (quem chama quem, a volta, o laço, o erro) e as sugestões (o molde
// da documentação do Python para uma forma do seu código). Elas acompanham as linhas enquanto você
// digita e se refazem no próximo Ctrl+S.

const vscode = require("vscode");
const cp = require("child_process");
const fs = require("fs");
const path = require("path");
const fluxograma = require("./fluxograma");

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
};
const DA_LEITURA = new Set(["escrita"]);
const RESERVA_DOS_VALORES = 36;   // letras para os valores ao lado da linha, quando há setas depois deles

let decoracoes = {};
let camada = {};               // o que não é chip: a descrição na coluna, as setas, as sugestões
let diagnosticos;
let barra;
let processos = new Map();     // arquivo → processo do motor em andamento
let leituras = new Map();      // arquivo → { processo, temporizador }
let ultimaLeitura = new Map(); // arquivo → a última leitura desenhada (redesenhada depois dos valores)
let pythons = new Map();       // arquivo → o Python achado (a leitura roda a cada tecla: achar uma vez só)
let extrasDe = new Map();      // arquivo → [largura dos valores ao lado de cada linha], do último salvamento
let setasDe = new Map();       // arquivo → { maiorX }: onde terminam as setas (a descrição vem depois)
let pedidas = new Set();       // arquivos salvos esperando a leitura do texto salvo para desenhar as setas

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
  // cada peça traz o próprio estilo: a posição em letras, a cor do tema
  camada.descricao = vscode.window.createTextEditorDecorationType({ before: { contentText: "" } });
  camada.setas = vscode.window.createTextEditorDecorationType({ before: { contentText: "" } });
  camada.trecho = vscode.window.createTextEditorDecorationType({});       // o pedaço da sugestão: o mouse mostra a ficha
  camada.lampada = vscode.window.createTextEditorDecorationType({
    gutterIconPath: path.join(__dirname, "lampada.svg"), gutterIconSize: "70%",
    light: { gutterIconPath: path.join(__dirname, "lampada-clara.svg") },
  });
  camada.espaco = vscode.window.createTextEditorDecorationType({ after: { contentText: "" } });  // a rolagem alcança a coluna
}

const cfg = (doc, chave) => vscode.workspace.getConfiguration("truecoral", doc.uri).get(chave);
const linhasDe = (doc) => Array.from({ length: doc.lineCount }, (_, i) => doc.lineAt(i).text);
const tabDe = (editor) => (typeof editor.options.tabSize === "number" ? editor.options.tabSize : 4);

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
  if (tambemLeitura) {
    for (const d of Object.values(camada)) editor.setDecorations(d, []);
    setasDe.delete(editor.document.uri.fsPath);
  }
  diagnosticos.delete(editor.document.uri);
}

async function pythonDe(documento) {
  const chave = documento.uri.fsPath;
  if (!pythons.has(chave)) pythons.set(chave, await acharPython(documento));
  return pythons.get(chave);
}

// ── a leitura: a cada tecla, sem rodar nada ─────────────────────────────────
// A descrição fica numa coluna alinhada, depois das setas, com a cara de um comentário: "# o que a linha faz".
// Na coluna, a frase curta; o mouse em cima mostra a inteira, com a história da variável.
function desenharLeitura(editor, r) {
  const doc = editor.document;
  const fimDa = (n) => doc.lineAt(n).range.end;
  const escrita = [], descricoes = [];
  if (cfg(doc, "descrever")) {
    const linhas = linhasDe(doc);
    const tab = tabDe(editor);
    const extras = doc.isDirty ? [] : (extrasDe.get(doc.uri.fsPath) || []);
    const setas = setasDe.get(doc.uri.fsPath);
    const D = fluxograma.colunaDaDescricao({ linhas, extras, tab, maiorX: setas ? setas.maiorX : null });
    let maisLonga = null;
    for (const [chave, linha] of Object.entries(r.linhas || {})) {
      const n = parseInt(chave, 10) - 1;
      if (n < 0 || n >= doc.lineCount || !linha.descricao) continue;
      const fim = fluxograma.larguraVisual(linhas[n], tab) + (extras[n] || 0);
      const col = Math.max(D, fim + 3);
      const texto = "# " + (linha.curta || linha.descricao);
      if (!maisLonga || col + texto.length > maisLonga.ate) maisLonga = { n, fim, ate: col + texto.length };
      descricoes.push({ range: new vscode.Range(fimDa(n), fimDa(n)),      // presa ao fim da linha: o mouse em cima abre a frase inteira
        hoverMessage: new vscode.MarkdownString("— " + linha.descricao.replace(/; depois, /, ";\n\ndepois, ").replace(/; /g, ";\n\n")),
        renderOptions: { before: { contentText: texto, textDecoration: "none; position: absolute; " +
          `left: ${col}ch; top: 0; white-space: pre; font-style: italic; color: var(--vscode-editorCodeLens-foreground);` } } });
    }
    // a coluna pode passar da largura da tela: um espaço invisível no fim da linha mais longa deixa rolar até ela
    editor.setDecorations(camada.espaco, maisLonga ? [{ range: new vscode.Range(fimDa(maisLonga.n), fimDa(maisLonga.n)),
      renderOptions: { after: { contentText: "", margin: `0 0 0 ${maisLonga.ate - maisLonga.fim + 2}ch` } } }] : []);
  } else {
    editor.setDecorations(camada.espaco, []);
  }
  const e = r.erro;
  if (e && e.linha && cfg(doc, "descrever")) {
    const n = Math.min(Math.max(e.linha - 1, 0), doc.lineCount - 1);
    escrita.push({ range: new vscode.Range(fimDa(n), fimDa(n)),
      hoverMessage: new vscode.MarkdownString(`${e.texto}\n\n*o Python diz:* \`${e.original}\``),
      renderOptions: { after: { contentText: " ✕ " + e.texto + " " } } });
  }
  editor.setDecorations(decoracoes.escrita, escrita);
  editor.setDecorations(camada.descricao, descricoes);
}

// ── as setas e as sugestões: ao salvar, sobre o texto salvo ─────────────────
function desenharSetas(editor) {
  const doc = editor.document;
  const arquivo = doc.uri.fsPath;
  const r = ultimaLeitura.get(arquivo);
  if (!r || r.versao !== doc.version || doc.isDirty) return;
  const setas = cfg(doc, "setas"), sugerir = cfg(doc, "sugestoes");
  const m = fluxograma.montar({ fluxo: r.fluxo, sugestoes: r.sugestoes || [], linhas: linhasDe(doc),
    extras: extrasDe.get(arquivo) || [], tab: tabDe(editor), setas, sugerir, foco: editor.selection.active.line + 1 });
  editor.setDecorations(camada.setas, m.pecas.map((p) => ({ range: new vscode.Range(p.linha, 0, p.linha, 0),
    renderOptions: { before: { contentText: p.texto, textDecoration: "none; " + p.css } } })));
  const naMargem = new Set();
  const trechos = [];
  if (sugerir) {
    for (const s of r.sugestoes || []) {
      const n = s.linha - 1;
      if (n < 0 || n >= doc.lineCount) continue;
      naMargem.add(n);
      trechos.push({ range: new vscode.Range(n, s.col, n, s.col_fim), hoverMessage: new vscode.MarkdownString(s.ficha) });
    }
  }
  editor.setDecorations(camada.trecho, trechos);
  editor.setDecorations(camada.lampada, [...naMargem].map((n) => new vscode.Range(n, 0, n, 0)));
  setasDe.set(arquivo, { maiorX: setas ? m.maiorX : null, emFoco: m.emFoco, foco: editor.selection.active.line + 1 });
  desenharLeitura(editor, r);                                // a coluna da descrição vem depois das setas
}

function ler(documento, espera) {
  if (!documento || documento.languageId !== "python" || documento.uri.scheme !== "file") return;
  if (!cfg(documento, "descrever") && !cfg(documento, "setas") && !cfg(documento, "sugestoes")) return;
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
          r.versao = versao;
          ultimaLeitura.set(arquivo, r);
          desenharLeitura(editor, r);
          if (pedidas.has(arquivo) && !documento.isDirty) { pedidas.delete(arquivo); desenharSetas(editor); }
        } catch (e) { /* uma leitura ruim não apaga a anterior */ }
      });
    filho.stdin.end(documento.getText());
    estado.processo = filho;
  }, espera);
}

function desenhar(editor, r) {
  const porTipo = Object.fromEntries(Object.keys(TIPOS).map((t) => [t, []]));
  const doc = editor.document;
  const extras = [];             // quanto os valores ocupam depois de cada linha: as setas passam depois deles
  for (const [chave, linha] of Object.entries(r.linhas || {})) {
    const n = parseInt(chave, 10) - 1;
    if (n < 0 || n >= doc.lineCount) continue;
    const fim = doc.lineAt(n).range.end;
    const detalhes = (linha.detalhes || []).filter(Boolean);
    let primeiro = true;
    // com as setas ligadas, os valores têm um espaço na linha: o que passa vira "…", e o mouse mostra inteiro
    const reserva = cfg(doc, "setas") ? RESERVA_DOS_VALORES : Infinity;
    let usado = 0;
    for (const chip of linha.chips || []) {
      if (chip.tipo === "erro" && r.erro && r.erro.escrita &&
          vscode.workspace.getConfiguration("truecoral", doc.uri).get("descrever")) continue;
      let texto = chip.texto;
      const custo = (t) => t.length + 2 + 2.4;                       // o texto, os espaços e a margem de 1.4em
      if (usado + custo(texto) > reserva) {
        const cabe = Math.floor(reserva - usado - 4.4);
        if (cabe < 6) break;
        texto = texto.slice(0, cabe - 1) + "…";
      }
      const partes = [];
      if (primeiro && detalhes.length) partes.push(detalhes.map((d) => d.includes("\n") ? "```\n" + d + "\n```" : d).join("\n\n"));
      if (texto !== chip.texto) partes.push("`" + chip.texto.replace(/`/g, "'") + "`");
      primeiro = false;
      usado += custo(texto);
      extras[n] = usado;
      (porTipo[chip.tipo] || porTipo.valor).push({
        range: new vscode.Range(fim, fim),
        hoverMessage: partes.length ? new vscode.MarkdownString(partes.join("\n\n")) : undefined,
        renderOptions: { after: { contentText: " " + texto + " " } },
      });
    }
  }
  for (const [tipo, lista] of Object.entries(porTipo)) {
    if (!DA_LEITURA.has(tipo)) editor.setDecorations(decoracoes[tipo], lista);   // a leitura é da outra camada
  }
  // com os valores na linha, as setas e a coluna da descrição se refazem depois deles
  extrasDe.set(doc.uri.fsPath, extras);
  const leitura = ultimaLeitura.get(doc.uri.fsPath);
  if (leitura && leitura.versao === doc.version && !doc.isDirty) desenharSetas(editor);
  else if (leitura) desenharLeitura(editor, leitura);

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
    ...Object.values(decoracoes), ...Object.values(camada),
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
      else if (ed) { ed.setDecorations(camada.descricao, []); ed.setDecorations(camada.espaco, []); ed.setDecorations(decoracoes.escrita, []); }
      vscode.window.showInformationMessage(`True Coral, descrição das linhas: ${novo ? "ligada" : "desligada"}`);
    }),
    ...["setas", "sugestoes"].map((chave) => vscode.commands.registerCommand(
      chave === "setas" ? "truecoral.alternarSetas" : "truecoral.alternarSugestoes", async () => {
        const c = vscode.workspace.getConfiguration("truecoral");
        const novo = !c.get(chave);
        await c.update(chave, novo, vscode.ConfigurationTarget.Global);
        const ed = vscode.window.activeTextEditor;
        if (ed && !ed.document.isDirty) { pedidas.add(ed.document.uri.fsPath); ler(ed.document, 0); }
        vscode.window.showInformationMessage(`True Coral, ${chave === "setas" ? "setas do fluxo" : "sugestões"}: ${novo ? "ligadas" : "desligadas"}`);
      })),
    vscode.commands.registerCommand("truecoral.alternar", async () => {
      const cfg = vscode.workspace.getConfiguration("truecoral");
      const novo = !cfg.get("aoSalvar");
      await cfg.update("aoSalvar", novo, vscode.ConfigurationTarget.Global);
      vscode.window.showInformationMessage(`True Coral ao salvar: ${novo ? "ligado" : "desligado"}`);
    }),
    vscode.workspace.onDidSaveTextDocument((doc) => {
      if (doc.languageId !== "python") return;
      if (!cfg(doc, "aoSalvar")) extrasDe.delete(doc.uri.fsPath);
      pedidas.add(doc.uri.fsPath);          // as setas nascem da leitura do texto salvo
      ler(doc, 0);
      if (cfg(doc, "aoSalvar")) analisar(doc);
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
      extrasDe.delete(doc.uri.fsPath); setasDe.delete(doc.uri.fsPath); pedidas.delete(doc.uri.fsPath);
    }),
    vscode.workspace.onDidChangeConfiguration((ev) => { if (ev.affectsConfiguration("truecoral.pythonPath")) pythons.clear(); }),
    // arquivo grande: as setas são as da função do cursor; o cursor mudou de função, as setas mudam junto
    vscode.window.onDidChangeTextEditorSelection((ev) => {
      const ed = ev.textEditor, arquivo = ed.document.uri.fsPath, estado = setasDe.get(arquivo);
      if (!estado || !estado.emFoco || ed.document.isDirty) return;
      clearTimeout(estado.temporizador);
      estado.temporizador = setTimeout(() => {
        const r = ultimaLeitura.get(arquivo);
        const linha = ed.selection.active.line + 1;
        const corpo = (l) => ((r && r.fluxo && r.fluxo.corpos) || []).filter((c) => c.linha <= l && l <= c.fim)
          .sort((a, b) => (a.fim - a.linha) - (b.fim - b.linha))[0];
        if (corpo(linha) !== corpo(estado.foco) || (!corpo(linha) && Math.abs(linha - estado.foco) > 20)) desenharSetas(ed);
      }, 300);
    }),
    vscode.window.onDidChangeVisibleTextEditors((eds) => {   // um arquivo salvo que volta à tela: setas de novo
      for (const ed of eds) if (!ed.document.isDirty && ed.document.languageId === "python") { pedidas.add(ed.document.uri.fsPath); ler(ed.document, 0); }
    }),
  );
  for (const ed of vscode.window.visibleTextEditors) {
    if (!ed.document.isDirty) pedidas.add(ed.document.uri.fsPath);      // ao abrir, o arquivo salvo já ganha as setas
    ler(ed.document, 0);
  }
}

function deactivate() {
  for (const p of processos.values()) p.kill();
  for (const l of leituras.values()) { clearTimeout(l.temporizador); if (l.processo) l.processo.kill(); }
}

module.exports = { activate, deactivate };
