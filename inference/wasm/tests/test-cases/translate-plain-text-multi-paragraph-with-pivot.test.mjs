/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { describe } from "vitest";
import { runTranslationTest } from "./test-cases/shared.mjs";

/**
 * This file tests the WASM bindings for pivot translation requests
 * that contain plain text with multiple paragraphs, without HTML tags.
 */
const testCases = [
  {
    sourceLanguage: "es",
    targetLanguage: "fr",
    sourceText:
      "El perro azul. Está corriendo por el parque.\n\nParece muy feliz. Juega con otros perros.",
    expectedText:
      "Le chien bleu. Il court à travers le parc.\n\nIl a l'air très heureux. Jouez avec d'autres chiens.",
  },
  {
    sourceLanguage: "fr",
    targetLanguage: "es",
    sourceText:
      "Le chien bleu. Il court dans le parc.\n\nIl semble très heureux. Il joue avec d'autres chiens.",
    expectedText:
      "El perro azul. Corre en el parque.\n\nParece muy feliz. Juega con otros perros.",
  },
  {
    sourceLanguage: "zh",
    targetLanguage: "es",
    sourceText:
      "蓝色的狗。它在公园里跑。\n\n它看起来很开心。它和其他狗一起玩。",
    expectedText:
      "El perro azul. Corre en el parque.\n\nParece muy feliz. Está jugando con otros perros.",
  },
  {
    sourceLanguage: "zh",
    targetLanguage: "fr",
    sourceText:
      "蓝色的狗。它在公园里跑。\n\n它看起来很开心。它和其他狗一起玩。",
    expectedText:
      "Le chien bleu. Il court dans le parc.\n\nIl semble très heureux. Il joue avec d'autres chiens.",
  },
];

describe("Plain-Text Multi-Paragraph Pivot Translations", () => {
  testCases.forEach(runTranslationTest);
});
