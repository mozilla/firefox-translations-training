/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { describe } from "vitest";
import { runTranslationTest } from "./test-cases/shared.mjs";

/**
 * This file tests the WASM bindings for pivot translation requests
 * that contain HTML tags within the source text, extended to multiple sentences.
 */
const testCases = [
  {
    sourceLanguage: "es",
    targetLanguage: "fr",
    sourceText:
      "<b>El perro</b> azul. <i>Está corriendo</i> por el parque. Parece muy feliz.",
    expectedText:
      "<b>Le chien</b> bleu. <i>Il court</i> à travers le parc. Il a l'air très heureux.",
    isHTML: true,
  },
  {
    sourceLanguage: "fr",
    targetLanguage: "es",
    sourceText:
      "<b>Le chien</b> bleu. <i>Il court</i> dans le parc. Il semble très heureux.",
    expectedText:
      "<b>El perro</b> azul. <i>Corre</i> en el parque. Parece muy feliz.",
    isHTML: true,
  },
  {
    sourceLanguage: "zh",
    targetLanguage: "es",
    sourceText: "蓝色的<b>狗</b>。<i>它在公园里跑</i>。它看起来很开心。",
    expectedText:
      "El <b>perro</b> azul. <i>Corre en el parque</i>. Parece muy feliz.",
    isHTML: true,
  },
  {
    sourceLanguage: "zh",
    targetLanguage: "fr",
    sourceText: "蓝色的<b>狗</b>。<i>它在公园里跑</i>。它看起来很开心。",
    expectedText:
      "Le <b>chien</b> bleu. <i>Il court dans le parc</i>. Il semble très heureux.",
    isHTML: true,
  },
];

describe("HTML Multi-Sentence Pivot Translations", () => {
  testCases.forEach(runTranslationTest);
});
