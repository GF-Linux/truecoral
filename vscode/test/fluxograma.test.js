// Os testes do fluxograma: node --test test/
const test = require("node:test");
const assert = require("node:assert");
const f = require("../fluxograma.js");

const LINHAS = [
  "def soma(a, b):",                          // 1
  "    return a + b",                         // 2
  "",                                         // 3
  "x = soma(1, 2)          # um comentário que é bem mais longo que o código de todas as linhas",  // 4
  "y = soma(3, 4)",                           // 5
  "z = soma(5, 6)",                           // 6
  "w = soma(7, 8)",                           // 7
];
const FLUXO = {
  funcoes: [{ nome: "soma", chave: "soma", linha: 1,
    chamadas: [4, 5, 6, 7].map((l) => ({ linha: l, args: "a, b" })),
    retornos: [{ linha: 2, texto: "a + b" }], caem: [] }],
  lacos: [], decisoes: [], erros: [], inicio: 4,
};
const colunaDe = (p) => Number((/left: (?:calc\()?([\d.]+)ch/.exec(p.css) || [])[1]);

test("a faixa passa depois do código, mas um comentário que ela só atravessa não a empurra", () => {
  const m = f.montar({ fluxo: { ...FLUXO, funcoes: [{ ...FLUXO.funcoes[0], chamadas: [{ linha: 5, args: "" }] }] }, linhas: LINHAS });
  const maiorCodigo = Math.max(...LINHAS.slice(0, 5).map((l) => f.larguraVisual(l.split("#")[0], 4)));
  for (const fx of m.faixas) {
    assert.ok(fx.x > maiorCodigo, `faixa em ${fx.x}`);
    assert.ok(fx.x < f.larguraVisual(LINHAS[3], 4), "o comentário da linha 4 não empurrou a faixa");
  }
});

test("chamadas em linhas seguidas viram um pente: um traço só até a faixa", () => {
  const m = f.montar({ fluxo: FLUXO, linhas: LINHAS });
  const ida = m.faixas.find((x) => x.tipo === "ida");
  const ateAFaixa = m.pecas.filter((p) => /border-top/.test(p.css) && /box-shadow/.test(p.css) && p.linha >= 3 && p.linha <= 6);
  assert.ok(ateAFaixa.length <= 2, `${ateAFaixa.length} traços longos`);    // um da ida, um da volta
  assert.ok(ida.x > 0);
});

test("o rótulo da chamada junta as linhas seguidas", () => {
  assert.strictEqual(f.listaDeLinhas([31, 32, 33, 34, 40]), "31 a 34 e 40");
  assert.strictEqual(f.listaDeLinhas([51, 58, 68]), "51, 58 e 68");
  // o rótulo precisa de uma linha vazia ao lado do def: aqui, a linha 2
  const linhas = ["def soma(a, b):", "", "    return a + b", "x = soma(1, 2)", "y = soma(3, 4)", "z = soma(5, 6)", "w = soma(7, 8)"];
  const fluxo = { ...FLUXO, funcoes: [{ ...FLUXO.funcoes[0], retornos: [{ linha: 3, texto: "a + b" }] }] };
  const m = f.montar({ fluxo, linhas });
  assert.ok(m.pecas.some((p) => p.linha === 1 && p.texto === "chamada 4 vezes: linhas 4 a 7"));
});

test("a coluna conta o tab como na tela", () => {
  assert.strictEqual(f.colunaVisual("\tx = 1", 1, 4), 4);
  assert.strictEqual(f.colunaVisual("ab\tc", 3, 4), 4);
});

test("a ordem das faixas cruza o mínimo", () => {
  // f chamada nas linhas 10 e 30; g chamada só na 20 (dentro do caminho de f): g por dentro não cruza nada
  const linhas = Array.from({ length: 30 }, (_, i) => `linha_${i + 1}`);
  const fluxo = { funcoes: [
    { nome: "f", chave: "f", linha: 1, chamadas: [{ linha: 10, args: "" }, { linha: 30, args: "" }], retornos: [], caem: [] },
    { nome: "g", chave: "g", linha: 15, chamadas: [{ linha: 20, args: "" }], retornos: [], caem: [] },
  ], lacos: [], decisoes: [], erros: [], inicio: null };
  const m = f.montar({ fluxo, linhas });
  const x = Object.fromEntries(m.faixas.map((fx) => [fx.nome, fx.x]));
  assert.ok(x.g < x.f, "g, de caminho curto, fica por dentro");
});

test("o texto cinza da sugestão não atravessa a faixa: termina na seta, em cima do pedaço", () => {
  // a linha 3 fica com o rótulo da volta; o cinza vai para a 5, logo abaixo do pedaço
  const linhas = ["def f():", "    return 1, 2", "", "for k in f()[0], 2:", "", "    print(k)", "print(f())"];
  const fluxo = { funcoes: [{ nome: "f", chave: "f", linha: 1, chamadas: [{ linha: 4, args: "" }, { linha: 7, args: "" }],
    retornos: [{ linha: 2, texto: "1, 2" }], caem: [] }], lacos: [], decisoes: [], erros: [], inicio: null };
  const sugestoes = [{ tipo: "posicao", linha: 4, col: 12, col_fim: 15, cinza: "[0] não diz o que é: desempacote e dê um nome", ficha: "" }];
  for (const ultima of ["print(f())", "    print(f'{k}'); resultado = f()  # e a faixa vai mais para a direita"]) {
    const m = f.montar({ fluxo, sugestoes, linhas: [...linhas.slice(0, 6), ultima] });
    const cinza = m.pecas.find((p) => p.texto.includes("desempac"));
    const faixa = Math.min(...m.faixas.map((fx) => fx.x));
    if (!cinza) continue;                  // sem lugar: fica só a lâmpada e o pontilhado
    const ate = colunaDe(cinza) * 0.85 + cinza.texto.length * 0.85;
    assert.ok(ate <= faixa + 0.5, `o cinza vai até ${ate}, a faixa está em ${faixa}`);
  }
  const sem = f.montar({ fluxo, sugestoes, linhas });
  assert.ok(sem.pecas.some((p) => /dotted/.test(p.css) && p.linha === 3), "o pontilhado fica mesmo sem o texto");
});

test("sem setas nem sugestões, nada é desenhado", () => {
  const m = f.montar({ fluxo: FLUXO, linhas: LINHAS, setas: false, sugerir: false });
  assert.strictEqual(m.pecas.length, 0);
  assert.strictEqual(m.maiorX, null);
});

test("arquivo grande: só as setas da função do cursor, de quem ela chama e de quem chama ela", () => {
  const linhas = Array.from({ length: 400 }, (_, i) => `linha_${i + 1}`);
  const funcoes = [], corpos = [];
  for (let k = 0; k < 20; k++) {                       // 20 funções, cada uma chamada pela seguinte
    const ini = 1 + k * 20;
    corpos.push({ nome: `f${k}`, linha: ini, fim: ini + 15 });
    funcoes.push({ nome: `f${k}`, chave: `f${k}`, linha: ini, chamadas: k < 19 ? [{ linha: ini + 25, args: "" }] : [], retornos: [], caem: [] });
  }
  const fluxo = { funcoes: funcoes.filter((x) => x.chamadas.length), corpos, lacos: [], decisoes: [], erros: [], inicio: null };
  const m = f.montar({ fluxo, linhas, foco: 105 });     // o cursor dentro de f5 (linhas 101 a 116)
  assert.ok(m.emFoco);
  const nomes = new Set(m.faixas.map((x) => x.nome));
  assert.ok(nomes.has("f5") && nomes.has("f4"), [...nomes].join(","));   // f5 é chamada por f6; f4 é chamada de dentro de f5
  assert.ok(m.faixas.length <= 8);
});
