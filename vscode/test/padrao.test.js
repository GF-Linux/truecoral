// os padrões escritos no extension.js (para quando o VS Code ainda não registrou um ajuste novo)
// têm que ser os mesmos do package.json
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");

test("os padrões do extension.js são os do package.json", () => {
  const raiz = path.join(__dirname, "..");
  const propriedades = require(path.join(raiz, "package.json")).contributes.configuration.properties;
  const fonte = fs.readFileSync(path.join(raiz, "extension.js"), "utf8");
  const padrao = Function("return " + /const PADRAO = (\{[^}]*\})/.exec(fonte)[1])();
  const doPacote = Object.fromEntries(Object.entries(propriedades).map(([k, p]) => [k.replace(/^truecoral\./, ""), p.default]));
  assert.deepStrictEqual(padrao, doPacote);
});
