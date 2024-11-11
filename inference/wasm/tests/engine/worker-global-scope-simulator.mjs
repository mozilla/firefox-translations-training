/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { isMainThread, parentPort } from "node:worker_threads";
import EventEmitter from "events";
import { readFileSync } from "fs";
import crypto from "crypto";

const BERGAMOT_HASH_PATH = "./generated/bergamot-translator.js.sha256";

/**
 * WorkerGlobalScopeSimulator simulates the WorkerGlobalScope in a Node.js worker_threads environment.
 *
 * It provides a minimal implementation of the Web Workers API by mapping required functions to their
 * Node.js `worker_threads` equivalents. This class allows us to test our code, intended for Web Workers
 * to be tested in a Node.js environment without modification.
 *
 * Note: Only the functionality required to rest the WASM translation bindings is implemented here.
 *       This is not a full implementation, nor is this intended for general-purpose use.
 *
 * https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API
 * https://nodejs.org/api/worker_threads.html
 *
 * @extends EventEmitter
 */
export default class WorkerGlobalScopeSimulator extends EventEmitter {
  /**
   * Constructs a new WorkerGlobalScopeSimulator instance.
   *
   * Initializes event handling to receive messages from the parent thread and emits
   * them as 'message' events to simulate the Web Workers messaging API.
   *
   * @throws {Error} If instantiated from the main thread instead of a worker thread.
   */
  constructor() {
    super();

    WorkerGlobalScopeSimulator.#ensureThreadIsWorker();

    parentPort.on("message", (data) => {
      this.emit("message", { data });
    });
  }

  /**
   * Ensures that the code is running inside a worker thread.
   *
   * @throws {Error} If called from the main thread.
   */
  static #ensureThreadIsWorker() {
    if (isMainThread || !parentPort) {
      throw new Error(`
        Attempt to call ${this.name} from the main thread.
        ${this.name} should only be used within a worker thread.
      `);
    }
  }

  /**
   * Reads and verifies the script by comparing its hash with the expected hash.
   *
   * @param {string} scriptPath - Path to the script to read and verify.
   * @returns {string} The content of the verified script.
   * @throws {Error} If the hash does not match or files cannot be read.
   */
  static #readAndVerifyScript(scriptPath) {
    const hashFileContent = readFileSync(BERGAMOT_HASH_PATH, {
      encoding: "utf-8",
    });
    const [expectedHash] = hashFileContent.trim().split(/\s+/);
    if (!expectedHash) {
      throw new Error(`Unable to extract hash from ${BERGAMOT_HASH_PATH}`);
    }

    const scriptContent = readFileSync(scriptPath, { encoding: "utf-8" });
    const scriptContentHash = crypto
      .createHash("sha256")
      .update(scriptContent, "utf8")
      .digest("hex");

    if (scriptContentHash !== expectedHash) {
      throw new Error(`Hash mismatch for script ${scriptPath}
         Expected: ${expectedHash}
         Received: ${scriptContentHash}
      `);
    }

    return scriptContent;
  }

  /**
   * Imports and executes a script, simulating the importScripts() function
   * available in Web Workers.
   *
   * This function executes eval.call() and is not intended for general-purpose
   * use. This is why it only takes a single script argument and validates that
   * the script matches the expected hash before evaluating.
   *
   * @param {string} scriptPath - Path to the script to import and execute.
   * @throws {Error} If the script fails to import or execute.
   */
  importScripts(scriptPath) {
    WorkerGlobalScopeSimulator.#ensureThreadIsWorker();

    try {
      const scriptContent =
        WorkerGlobalScopeSimulator.#readAndVerifyScript(scriptPath);
      eval.call(globalThis, scriptContent);
    } catch (error) {
      throw new Error(`
        🚨 Failed to read or import the required script for translation 🚨

        ${error}
 
        ⏩ NEXT STEPS ⏩
 
        To ensure that test dependencies are properly set up, please run the following command:
 
        ❯ task inference-test-wasm
      `);
    }
  }

  /**
   * Adds an event listener for the specified event type.
   *
   * @param {string} event - The event type to listen for.
   * @param {Function} listener - The function to call when the event occurs.
   */
  addEventListener(event, listener) {
    WorkerGlobalScopeSimulator.#ensureThreadIsWorker();
    this.on(event, listener);
  }

  /**
   * Removes an event listener for the specified event type.
   *
   * @param {string} event - The event type to stop listening for.
   * @param {Function} listener - The function to remove.
   */
  removeEventListener(event, listener) {
    WorkerGlobalScopeSimulator.#ensureThreadIsWorker();
    this.off(event, listener);
  }

  /**
   * Posts a message to the parent thread, simulating the `postMessage` function
   * available in Web Workers.
   *
   * @param {any} message - The message to send to the parent thread.
   */
  postMessage(message) {
    WorkerGlobalScopeSimulator.#ensureThreadIsWorker();
    parentPort.postMessage(message);
  }
}
