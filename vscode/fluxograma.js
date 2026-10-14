// O fluxograma: das ligações que a leitura achou (quem chama quem, onde volta, laços, decisões, erros)
// para as peças que a extensão desenha por cima do código.
//
// Não depende do VS Code: recebe o texto das linhas e devolve peças. Cada peça vive numa linha só
// (um pedaço de faixa, uma ponta de seta, um rótulo) e é posicionada em "ch", a largura de uma letra da
// fonte do próprio editor — a seta cai na coluna certa com qualquer fonte, sem medir nada. Como cada
// peça é presa à sua linha, elas acompanham a rolagem e as linhas que o VS Code desenha aos poucos.
//
// As cores são as variáveis do tema (--vscode-...): o desenho segue o tema escuro, claro ou de alto
// contraste.

const COR = {
  // as cores claras do terminal: cada tema as escolhe para serem lidas sobre o próprio fundo
  funcoes: ["var(--vscode-terminal-ansiBrightBlue)", "var(--vscode-terminal-ansiBrightYellow)",
            "var(--vscode-terminal-ansiBrightGreen)", "var(--vscode-terminal-ansiBrightMagenta)",
            "var(--vscode-terminal-ansiBrightCyan)"],
  erro: "var(--vscode-terminal-ansiBrightRed)",
  cinza: "var(--vscode-editorCodeLens-foreground)",
  texto: "var(--vscode-editor-foreground)",
  fundo: "var(--vscode-editor-background)",
};
const FONTE_ROTULO = 0.85;     // os rótulos são menores que o código
const FOLGA = 4;               // letras entre uma faixa e a próxima
const DY = 5;                  // px: a ida sai um pouco acima do meio da linha, a volta chega um pouco abaixo

const n2 = (x) => Number(x.toFixed(2));

// a coluna na tela de uma posição do texto (o tab ocupa várias colunas)
function colunaVisual(texto, col, tab) {
  let v = 0;
  for (let i = 0; i < Math.min(col, texto.length); i++) v = texto[i] === "\t" ? v + tab - (v % tab) : v + 1;
  return v + Math.max(0, col - texto.length);
}

function larguraVisual(texto, tab) {
  return colunaVisual(texto.replace(/\s+$/, ""), texto.replace(/\s+$/, "").length, tab);
}

// o código da linha sem o comentário do fim (# fora de texto entre aspas): a parte que a faixa não pode cortar
function semComentario(texto) {
  let aspa = null;
  for (let i = 0; i < texto.length; i++) {
    const c = texto[i];
    if (aspa) { if (c === "\\") i++; else if (c === aspa) aspa = null; }
    else if (c === "'" || c === '"') aspa = c;
    else if (c === "#") return texto.slice(0, i);
  }
  return texto;
}

function recuo(texto, tab) {
  const m = /^[ \t]*/.exec(texto);
  return colunaVisual(texto, m[0].length, tab);
}

// "31, 32, 33 e 40" → intervalos seguidos viram "31 a 33"
function listaDeLinhas(nums) {
  const u = [...new Set(nums)].sort((a, b) => a - b);
  const partes = [];
  for (let i = 0; i < u.length; i++) {
    let j = i;
    while (j + 1 < u.length && u[j + 1] === u[j] + 1) j++;
    partes.push(j - i >= 2 ? `${u[i]} a ${u[j]}` : j > i ? `${u[i]}, ${u[j]}` : `${u[i]}`);
    i = j;
  }
  return partes.length === 1 ? partes[0] : partes.slice(0, -1).join(", ") + " e " + partes[partes.length - 1];
}

// ── as peças ────────────────────────────────────────────────────────────────
// linha: base 0 (a do editor). y em px a partir do meio da linha.
function peca(linha, css, texto) { return { linha, css: "position: absolute; pointer-events: none; " + css, texto: texto || "" }; }

function vertical(linha, x, de, ate, cor, tracejada, z) {
  // de/ate: "topo" | "base" | número (px a partir do meio)
  const y = (v) => v === "topo" ? "0%" : v === "base" ? "100%" : `calc(50% + ${v}px)`;
  return peca(linha, `left: calc(${n2(x)}ch - 1px); top: ${y(de)}; height: calc(${y(ate)} - ${y(de)}); width: 0; ` +
    `border-left: 2px ${tracejada ? "dashed" : "solid"} ${cor}; z-index: ${z};`);
}

function horizontal(linha, x0, x1, dy, cor, tracejada, halo) {
  const a = Math.min(x0, x1), b = Math.max(x0, x1);
  return peca(linha, `left: ${n2(a)}ch; width: ${n2(b - a)}ch; top: calc(50% + ${dy - 1}px); height: 0; ` +
    `border-top: 2px ${tracejada ? "dashed" : "solid"} ${cor}; z-index: 3;` +
    (halo ? ` box-shadow: 0 0 0 2px ${COR.fundo};` : ""));
}

function ponta(linha, x, dy, direcao, cor) {
  // um triângulo de bordas; x é a coluna da ponta
  const t = 4, c = 7;
  const forma = {
    esquerda: `border-top: ${t}px solid transparent; border-bottom: ${t}px solid transparent; border-right: ${c}px solid ${cor}; left: ${n2(x)}ch; top: calc(50% + ${dy - t}px);`,
    direita: `border-top: ${t}px solid transparent; border-bottom: ${t}px solid transparent; border-left: ${c}px solid ${cor}; left: calc(${n2(x)}ch - ${c}px); top: calc(50% + ${dy - t}px);`,
    cima: `border-left: ${t}px solid transparent; border-right: ${t}px solid transparent; border-bottom: ${c}px solid ${cor}; left: calc(${n2(x)}ch - ${t}px); top: calc(50% + ${dy}px);`,
    baixo: `border-left: ${t}px solid transparent; border-right: ${t}px solid transparent; border-top: ${c}px solid ${cor}; left: calc(${n2(x)}ch - ${t}px); top: calc(50% + ${dy - c}px);`,
  }[direcao];
  return peca(linha, `width: 0; height: 0; z-index: 5; ${forma}`);
}

function rotulo(linha, col, texto, cor, extra = "") {
  return peca(linha, `left: ${n2(col / FONTE_ROTULO)}ch; top: 50%; transform: translateY(-50%); font-size: ${FONTE_ROTULO}em; ` +
    `white-space: pre; color: ${cor}; background: ${COR.fundo}; padding: 0 2px; z-index: 6; ${extra}`, texto);
}

// ── a montagem ──────────────────────────────────────────────────────────────
// entrada: { fluxo, sugestoes, linhas: [texto], extras: [largura a mais por linha (os valores ao lado)],
//            tab, setas: bool, sugerir: bool }
// saída:   { pecas, faixas: [{x, de, ate}], cinzas, sublinhados }
// foco: a linha do cursor. Num arquivo com mais de LIMITE_DE_FAIXAS faixas, só aparecem as da função onde o
// cursor está — quem ela chama e quem chama ela —; num arquivo pequeno, todas.
const LIMITE_DE_FAIXAS = 8;

function montar({ fluxo, sugestoes = [], linhas, extras = [], tab = 4, setas = true, sugerir = true, foco = null }) {
  const N = linhas.length;
  const fim = (n) => (n >= 1 && n <= N ? larguraVisual(linhas[n - 1], tab) + (extras[n - 1] || 0) : 0);
  // por onde a faixa só passa, um comentário longo não a empurra: ela passa por cima, mais clara
  const codigo = (n) => (n >= 1 && n <= N ? larguraVisual(semComentario(linhas[n - 1]), tab) + (extras[n - 1] || 0) : 0);
  const vazia = (n) => n >= 1 && n <= N && linhas[n - 1].trim() === "";
  const ocupadas = new Set();
  const pecas = [];
  const faixas = [];
  const depois = [];          // rótulos de menos importância: escolhem a linha por último
  let emFoco = false;

  // um lugar para um texto: a linha vazia logo abaixo, senão a logo acima
  const lugar = (n, preferir = [1, -1]) => {
    for (const d of preferir) {
      const m = n + d;
      if (vazia(m) && !ocupadas.has(m)) { ocupadas.add(m); return { linha: m, d }; }
    }
    return null;
  };

  if (setas && fluxo) {
    // 1. as faixas das funções: a ida (chamada → def) e a volta (return → quem chamou)
    fluxo.funcoes.forEach((f, i) => {
      const cor = COR.funcoes[i % COR.funcoes.length];
      const chamadas = f.chamadas.map((c) => c.linha);
      faixas.push({ funcao: f, tipo: "ida", cor, tracejada: false,
        pontas: [...chamadas.map((l) => ({ linha: l, dy: -DY, fonte: true })), { linha: f.linha, dy: 0, alvo: true }] });
      const fontes = [...f.retornos.map((r) => ({ linha: r.linha, dy: 0, fonte: true })),
                      ...f.caem.map((c) => ({ linha: c.linha, dy: 0, fonte: true, cor: COR.erro }))];
      if (fontes.length) {
        faixas.push({ funcao: f, tipo: "volta", cor, tracejada: true,
          pontas: [...fontes, ...chamadas.map((l) => ({ linha: l, dy: DY, alvo: true }))] });
      }
    });
    if (faixas.length > LIMITE_DE_FAIXAS) {
      const corpos = fluxo.corpos || [];
      const dentro = foco === null ? null
        : corpos.filter((c) => c.linha <= foco && foco <= c.fim).sort((a, b) => (a.fim - a.linha) - (b.fim - b.linha))[0];
      const perto = (l) => dentro ? l >= dentro.linha && l <= dentro.fim : foco !== null && Math.abs(l - foco) <= 40;
      const ligadas = faixas.filter((fx) => (dentro && fx.funcao.linha === dentro.linha) || fx.pontas.some((p) => perto(p.linha)));
      ligadas.sort((a, b) => Math.min(...a.pontas.map((p) => Math.abs(p.linha - (foco || 0)))) -
                             Math.min(...b.pontas.map((p) => Math.abs(p.linha - (foco || 0)))));
      faixas.splice(0, faixas.length, ...ligadas.slice(0, LIMITE_DE_FAIXAS));
      emFoco = true;
    }
    // linhas seguidas que chamam a mesma função viram um pente: um dente curto em cada linha e um
    // traço só até a faixa (dez chamadas não viram dez traços atravessando a tela)
    for (const fx of faixas) {
      fx.grupos = [];
      for (const tipo of ["fonte", "alvo"]) {
        const ps = fx.pontas.filter((p) => !!p[tipo] && !p.cor).sort((a, b) => a.linha - b.linha);
        let atual = [];
        const fechar = () => { if (atual.length >= 3) fx.grupos.push(atual); atual = []; };
        for (const p of ps) {
          if (atual.length && p.linha !== atual[atual.length - 1].linha + 1) fechar();
          atual.push(p);
        }
        fechar();
      }
      for (const g of fx.grupos) g.xc = Math.max(...g.map((p) => fim(p.linha))) + 2.5;
      fx.sozinhas = fx.pontas.filter((p) => !fx.grupos.some((g) => g.includes(p)));
      fx.efetivas = [...fx.sozinhas, ...fx.grupos.map((g) => ({ linha: g[Math.floor(g.length / 2)].linha, dy: g[0].dy, xc: g.xc }))];
      const ls = fx.efetivas.map((p) => p.linha);
      fx.de = Math.min(...ls); fx.ate = Math.max(...ls);
    }

    // 2. a ordem, de dentro para fora, que menos cruza: uma faixa por dentro de outra cruza cada
    //    ponta da de fora que caia no meio do seu caminho
    const custo = (dentro, fora) => fora.efetivas.filter((p) => p.linha > dentro.de && p.linha < dentro.ate).length;
    let ordem = [...faixas].sort((a, b) => (a.ate - a.de) - (b.ate - b.de) || a.de - b.de);
    for (let volta = 0, melhorou = true; melhorou && volta < 60; volta++) {
      melhorou = false;
      for (let i = 0; i + 1 < ordem.length; i++) {      // trocar dois vizinhos só muda o custo entre os dois
        const [a, b] = [ordem[i], ordem[i + 1]];
        if (custo(b, a) < custo(a, b)) { ordem[i] = b; ordem[i + 1] = a; melhorou = true; }
      }
    }

    // 3. a coluna de cada faixa: depois de tudo o que está escrito no caminho dela
    let anterior = -Infinity;
    for (const fx of ordem) {
      let maior = 0;
      for (let l = fx.de; l <= fx.ate; l++) maior = Math.max(maior, codigo(l));
      for (const p of fx.efetivas) maior = Math.max(maior, p.xc !== undefined ? p.xc : fim(p.linha));
      fx.x = Math.max(anterior + FOLGA, maior + 3);
      anterior = fx.x;
    }

    // 4. as peças de cada faixa
    for (const fx of ordem) {
      const naLinha = new Map();
      for (const p of fx.efetivas) {
        if (!naLinha.has(p.linha)) naLinha.set(p.linha, []);
        naLinha.get(p.linha).push(p);
      }
      for (let l = fx.de; l <= fx.ate && fx.ate > fx.de; l++) {
        const ps = naLinha.get(l);
        const z = ps ? 4 : 2;
        const de = l === fx.de ? Math.min(...ps.map((p) => p.dy)) : "topo";
        const ate = l === fx.ate ? Math.max(...ps.map((p) => p.dy)) : "base";
        const v = vertical(l - 1, fx.x, de, ate, fx.cor, fx.tracejada, z);
        if (fim(l) > fx.x - 1) v.css += " opacity: 0.35;";           // por cima de um comentário
        pecas.push(v);
      }
      for (const g of fx.grupos) {
        const alvo = !!g[0].alvo, dy = g[0].dy;
        const xc = g.xc;
        for (const p of g) {
          const x0 = fim(p.linha) + (alvo ? 1 : 0.6);
          pecas.push(horizontal(p.linha - 1, x0, xc, dy, fx.cor, fx.tracejada, false));
          if (alvo) pecas.push(ponta(p.linha - 1, x0, dy, "esquerda", fx.cor));
        }
        for (let l = g[0].linha; l <= g[g.length - 1].linha; l++) {
          pecas.push(vertical(l - 1, xc, l === g[0].linha ? dy : "topo", l === g[g.length - 1].linha ? dy : "base", fx.cor, fx.tracejada, 4));
        }
        const meio = g[Math.floor(g.length / 2)].linha;              // o traço até a faixa sai do meio do pente
        pecas.push(horizontal(meio - 1, xc, fx.x, dy, fx.cor, fx.tracejada, true));
      }
      for (const p of fx.sozinhas) {
        const cor = p.cor || fx.cor;
        const x0 = fim(p.linha) + (p.alvo ? 1 : 0.6);
        pecas.push(horizontal(p.linha - 1, x0, fx.x, p.dy, cor, fx.tracejada, true));
        if (p.alvo) pecas.push(ponta(p.linha - 1, x0, p.dy, "esquerda", cor));
      }
    }

    // 5. os rótulos das faixas, numa linha vazia ao lado da ponta
    for (const fx of faixas) {
      const f = fx.funcao;
      const chamadas = f.chamadas.map((c) => c.linha);
      if (fx.tipo === "ida") {
        const texto = f.chamadas.length === 1
          ? (f.chamadas[0].args ? `${f.chamadas[0].args} · vindo da linha ${chamadas[0]}` : `chamada na linha ${chamadas[0]}`)
          : `chamada ${f.chamadas.length} vezes: linhas ${listaDeLinhas(chamadas)}`;
        const onde = lugar(f.linha);
        if (onde) pecas.push(rotulo(onde.linha - 1, Math.max(fim(f.linha) + 1, recuo(linhas[f.linha - 1], tab) + 2), texto, fx.cor));
      } else {
        const para = chamadas.length === 1 ? `linha ${chamadas[0]}` : "quem chamou";
        if (f.retornos.length) {
          const r = f.retornos[0];
          const texto = chamadas.length === 1 ? `${r.texto} → ${para}` : "volta para quem chamou";
          const onde = lugar(r.linha);
          if (onde) pecas.push(rotulo(onde.linha - 1, fim(r.linha) + 1, texto, fx.cor));
        }
        for (const c of f.caem) {
          const onde = lugar(c.linha);
          if (onde) pecas.push(rotulo(onde.linha - 1, fim(c.linha) + 1, `${c.motivo}: None → ${para}`, COR.erro));
        }
      }
    }

    // 6. dentro das funções: o laço volta, a decisão diz sim e não, o erro cai no except
    for (const l of fluxo.lacos) {
      const col = colunaVisual(linhas[l.linha - 1] || "", l.col, tab);
      const corpo = recuo(linhas[l.fim - 1] || "", tab);
      const esquerda = col >= 2;
      const x = esquerda ? col - 1.6 : col + 1.5;
      pecas.push(horizontal(l.fim - 1, x, corpo - 0.3, 7, COR.cinza, false, false));
      for (let k = l.linha; k <= l.fim; k++) {
        pecas.push(vertical(k - 1, x, k === l.linha ? (esquerda ? 0 : "base") : "topo", k === l.fim ? 8 : "base", COR.cinza, false, 2));
      }
      if (esquerda) pecas.push(ponta(l.linha - 1, col - 0.15, 0, "direita", COR.cinza));
      else pecas.push(ponta(l.linha, x, -10, "cima", COR.cinza));
      depois.push(() => {
        for (let k = l.linha + 1; k < l.fim; k++) {
          if (vazia(k) && !ocupadas.has(k)) { ocupadas.add(k); pecas.push(rotulo(k - 1, x + 0.5, "repete", COR.cinza, "background: transparent;")); break; }
        }
      });
    }
    for (const d of fluxo.decisoes) {
      const col = colunaVisual(linhas[d.linha - 1] || "", d.col, tab);
      for (const [l, txt] of [[d.sim, "sim"], [d.nao, "não"]]) {
        if (l && recuo(linhas[l - 1] || "", tab) - col >= 4) pecas.push(rotulo(l - 1, col + 0.3, txt, COR.cinza, "background: transparent;"));
      }
    }
    for (const e of fluxo.erros) {
      const col = colunaVisual(linhas[e.de - 1] || "", e.col, tab);
      const colTry = colunaVisual(linhas[e.para - 1] || "", e.col_try, tab);
      const esquerda = colTry >= 2;
      const x = esquerda ? colTry - 1.2 : colTry + 1.5;
      let linhaH = e.de, dyH = 7;
      if (vazia(e.de + 1) && e.de + 1 < e.para) {                 // desce pela linha vazia de baixo
        pecas.push(vertical(e.de - 1, col + 0.5, 7, "base", COR.erro, false, 4));
        pecas.push(vertical(e.de, col + 0.5, "topo", 0, COR.erro, false, 4));
        linhaH = e.de + 1; dyH = 0;
        ocupadas.add(e.de + 1);
      }
      pecas.push(horizontal(linhaH - 1, x, linhaH === e.de ? col : col + 0.5, dyH, COR.erro, false, false));
      for (let k = linhaH; k <= e.para; k++) {
        const de = k === linhaH ? dyH : "topo";
        const ate = k === e.para ? (esquerda ? 0 : -8) : "base";
        pecas.push(vertical(k - 1, x, de, ate, COR.erro, false, 4));
      }
      if (esquerda) {
        pecas.push(horizontal(e.para - 1, x, colTry - 0.2, 0, COR.erro, false, false));
        pecas.push(ponta(e.para - 1, colTry - 0.1, 0, "direita", COR.erro));
      } else {
        pecas.push(ponta(e.para - 1, x, -1, "baixo", COR.erro));
      }
    }
    depois.push(() => {
    if (fluxo.inicio && vazia(fluxo.inicio - 1) && !ocupadas.has(fluxo.inicio - 1)) {
      ocupadas.add(fluxo.inicio - 1);
      pecas.push(rotulo(fluxo.inicio - 2, 0, "▶ o programa começa a rodar aqui; acima, só se definem funções", COR.texto,
        "opacity: 0.75;"));
    }
    });
  }

  // 7. as sugestões: um pontilhado no pedaço e, numa linha vazia ao lado, o texto cinza
  const cinzas = [];
  if (sugerir) {
    const vistas = new Set();
    for (const s of sugestoes) {
      const col = colunaVisual(linhas[s.linha - 1] || "", s.col, tab);
      const colFim = colunaVisual(linhas[s.linha - 1] || "", s.col_fim, tab);
      cinzas.push({ ...s, colVisual: col, colFimVisual: colFim });
      pecas.push(peca(s.linha - 1, `left: ${n2(col)}ch; width: ${n2(colFim - col)}ch; top: calc(100% - 3px); height: 0; ` +
        `border-top: 1px dotted ${COR.cinza}; z-index: 1;`));
      if (vistas.has(s.linha)) continue;                 // numa linha, o texto cinza é o da primeira
      vistas.add(s.linha);
      const onde = lugar(s.linha);
      if (!onde) continue;
      let limite = Infinity;                             // o texto termina antes da primeira faixa que passa ali
      for (const fx of faixas) if (fx.x !== undefined && onde.linha >= fx.de && onde.linha <= fx.ate) limite = Math.min(limite, fx.x - 1);
      const seta = onde.d === 1 ? "↑" : "↓";
      let texto = `${seta} ${s.cinza}`, inicio = col;
      const largura = (t) => t.length * FONTE_ROTULO;
      if (col + largura(texto) > limite) {
        const aEsquerda = `${s.cinza} ${seta}`;
        const comeca = col + 1 - largura(aEsquerda);
        const margem = Math.min(recuo(linhas[s.linha - 1] || "", tab), recuo(linhas[onde.linha - 1] || "", tab) || Infinity);
        if (comeca >= Math.min(margem, col)) { texto = aEsquerda; inicio = comeca; }
        else {
          const cabe = Math.floor((limite - col) / FONTE_ROTULO);
          if (cabe <= 12) continue;          // sem lugar: fica a lâmpada e o pontilhado, e o mouse mostra a ficha
          texto = texto.slice(0, cabe - 1) + "…";
        }
      }
      pecas.push(rotulo(onde.linha - 1, inicio, texto, COR.cinza, "background: transparent;"));
    }
  }

  for (const f of depois) f();

  const maiorX = faixas.reduce((m, fx) => (fx.x !== undefined ? Math.max(m, fx.x) : m), -Infinity);
  return { pecas, faixas: faixas.map((f) => ({ x: f.x, de: f.de, ate: f.ate, tipo: f.tipo, nome: f.funcao.nome })),
           maiorX: Number.isFinite(maiorX) ? maiorX : null, cinzas, emFoco };
}

// a coluna da descrição: depois das faixas (ou depois do código, se não houver faixas)
function colunaDaDescricao({ linhas, extras = [], tab = 4, maiorX = null, teto = 100 }) {
  if (maiorX !== null) return Math.ceil(maiorX + FOLGA);
  let maior = 0;
  linhas.forEach((t, i) => { maior = Math.max(maior, larguraVisual(t, tab) + (extras[i] || 0)); });
  return Math.min(maior + 4, teto);
}

module.exports = { montar, colunaDaDescricao, colunaVisual, larguraVisual, listaDeLinhas, COR };
