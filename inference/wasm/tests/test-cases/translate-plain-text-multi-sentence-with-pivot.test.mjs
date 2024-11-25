/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { describe } from "vitest";
import { runTranslationTest } from "./test-cases/shared.mjs";

/**
 * This file tests the WASM bindings for pivot translation requests
 * that contain plain text with multiple sentences, without HTML tags.
 */
const testCases = [
  {
    sourceLanguage: "es",
    targetLanguage: "fr",
    sourceText:
      "El perro azul. Está corriendo por el parque. Parece muy feliz.",
    expectedText:
      "Le chien bleu. Il court à travers le parc. Il a l'air très heureux.",
  },
  {
    sourceLanguage: "fr",
    targetLanguage: "es",
    sourceText: "Le chien bleu. Il court dans le parc. Il semble très heureux.",
    expectedText: "El perro azul. Corre en el parque. Parece muy feliz.",
  },
  {
    sourceLanguage: "zh",
    targetLanguage: "es",
    sourceText: "蓝色的狗。它在公园里跑。它看起来很开心。",
    expectedText: "El perro azul. Corre en el parque. Parece muy feliz.",
  },
  {
    sourceLanguage: "zh",
    targetLanguage: "fr",
    sourceText: "蓝色的狗。它在公园里跑。它看起来很开心。",
    expectedText:
      "Le chien bleu. Il court dans le parc. Il semble très heureux.",
  },
];

describe("Plain-Text Multi-Sentence Pivot Translations", () => {
  testCases.forEach(runTranslationTest);
});
