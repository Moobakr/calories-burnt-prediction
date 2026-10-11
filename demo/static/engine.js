"use strict";
// Deliberately narrow evaluator for our exported scalar squared-error trees.
// Float32 inputs, thresholds, leaves and sequential sums reproduce XGBoost CPU.
(() => {
  function validate(meta, payload) {
    if (!payload || typeof payload !== "object" || Array.isArray(payload) ||
        Object.keys(payload).sort().join(",") !== "inputs,mode") throw new Error("Send a mode and its inputs.");
    const {mode, inputs} = payload;
    if (typeof mode !== "string" || !Object.hasOwn(meta.systems, mode)) throw new Error("Choose a supported input mode.");
    const columns = meta.systems[mode].input_columns;
    if (!inputs || typeof inputs !== "object" || Array.isArray(inputs) ||
        Object.keys(inputs).sort().join(",") !== [...columns].sort().join(","))
      throw new Error("Supply exactly the fields required by this mode; missing sensors are not filled with zero.");
    for (const name of columns) {
      const value = inputs[name], schema = meta.fields[name];
      if (schema.categories) {
        if (typeof value !== "string" || !schema.categories.includes(value)) throw new Error(`${schema.label}: choose a recorded category.`);
      } else {
        if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`${schema.label}: enter a finite number.`);
        if (schema.integer && !Number.isInteger(value)) throw new Error(`${schema.label}: enter a whole number.`);
        if (value < schema.min || value > schema.max) throw new Error(`${schema.label}: use ${schema.min}–${schema.max} ${schema.unit} (development range).`);
      }
    }
    return {mode, inputs};
  }
  function predictForest(forest, inputs) {
    if (forest.format !== "calorie-lab-scalar-gbtree-v1") throw new Error("Unsupported exported model.");
    const row = forest.features.map(field => Math.fround(Object.hasOwn(field, "category") ? Number(inputs[field.name] === field.category) : inputs[field.name]));
    let prediction = Math.fround(forest.base_score);
    for (const tree of forest.trees) {
      let node = 0, steps = 0;
      while (tree.left[node] !== -1) {
        if (++steps > tree.left.length) throw new Error("Invalid exported tree.");
        node = row[tree.feature[node]] < Math.fround(tree.value[node]) ? tree.left[node] : tree.right[node];
      }
      prediction = Math.fround(prediction + Math.fround(tree.value[node]));
    }
    if (!Number.isFinite(prediction)) throw new Error("Model returned a nonfinite estimate.");
    return prediction;
  }
  function predict(meta, forests, payload) {
    const {mode, inputs} = validate(meta, payload), system = meta.systems[mode];
    const prediction = predictForest(forests[mode], inputs), q = system.threshold;
    const group = system.duration_groups.find(row => {
      const [lo, hi] = row.group.split("-").map(Number);
      return inputs.Duration >= lo && inputs.Duration <= hi;
    });
    if (!group) throw new Error("Duration group unavailable.");
    return {mode, model:system.name, prediction, lower:prediction-q, upper:prediction+q, nominal_coverage:.9,
      test_mae:system.test_mae, test_coverage:system.test_coverage, duration_group:group,
      negative_lower_bound:prediction-q < 0, input_fields:system.input_columns};
  }
  async function loadBundle() {
    const response = await fetch("./metadata.json", {cache:"no-cache"});
    if (!response.ok) throw new Error("Model metadata could not be loaded.");
    const meta = await response.json(), forests = {};
    await Promise.all(Object.entries(meta.systems).map(async ([mode, system]) => {
      if (!/^models\/(duration|basic|heart_rate|full)\.json$/.test(system.browser_artifact)) throw new Error("Invalid model path.");
      const file = await fetch(`./${system.browser_artifact}`, {cache:"no-cache"});
      if (!file.ok) throw new Error("Frozen model could not be loaded.");
      const bytes = await file.arrayBuffer();
      const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map(x => x.toString(16).padStart(2,"0")).join("");
      if (digest !== system.browser_sha256) throw new Error("Model integrity check failed. Reload the page.");
      forests[mode] = JSON.parse(new TextDecoder().decode(bytes));
    }));
    return {meta, forests};
  }
  const api = {validate, predictForest, predict, loadBundle};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else globalThis.CalorieInference = api;
})();
