"use strict";
const $ = (id) => document.getElementById(id);
const names = {heart_rate:"Basic + heart rate",full:"Full inputs",basic:"Basic inputs",duration:"Duration only"};
const help = {heart_rate:"6 fields. The primary model: heart rate included, temperature omitted.",full:"7 fields. Adds recorded temperature to the heart-rate model's inputs.",basic:"5 fields. A separate model for sessions without sensor readings; errors are larger.",duration:"1 field. A diagnostic baseline with much less information and larger errors."};
let forests, meta, values = {}, revision = 0, pending;
const fmt = (number, digits=1) => number.toLocaleString("en-US",{minimumFractionDigits:digits,maximumFractionDigits:digits});
function clearResult() {
  revision++;
  if (pending) pending.abort();
  $("result").hidden=true; $("empty-result").hidden=false;
  $("result-tag").textContent="Awaiting estimate";
  $("form-error").hidden=true;
  $("estimate").disabled=!meta;
}
function renderFields() {
  clearResult();
  const mode=$("mode").value;
  $("mode-help").textContent=help[mode];
  $("fields").replaceChildren();
  for (const name of meta.systems[mode].input_columns) {
    const schema=meta.fields[name], block=document.createElement("div"); block.className="field";
    const label=document.createElement("label"); label.htmlFor=`field-${name}`; label.textContent=schema.label;
    const input=document.createElement(schema.categories ? "select" : "input");
    input.id=`field-${name}`; input.name=name; input.required=true;
    if (schema.categories) {
      for (const category of schema.categories) { const option=document.createElement("option"); option.value=category; option.textContent=category[0].toUpperCase()+category.slice(1); input.append(option); }
    } else { input.type="number"; input.min=schema.min; input.max=schema.max; input.step=schema.integer ? "1" : "any"; input.inputMode=schema.integer ? "numeric" : "decimal"; }
    input.value=values[name] ?? "";
    const tip=document.createElement("p"); tip.className="field-help"; tip.id=`help-${name}`;
    tip.textContent=schema.categories ? "Categories recorded in this benchmark." : `${schema.min}–${schema.max} ${schema.unit} · development range`;
    input.setAttribute("aria-describedby",tip.id);
    input.addEventListener("input",()=>{values[name]=schema.categories ? input.value : (input.value==="" ? "" : Number(input.value)); clearResult();});
    block.append(label,input,tip); $("fields").append(block);
  }
  renderBenchmarks();
}
function renderBenchmarks() {
  $("benchmark-cards").replaceChildren();
  for (const mode of ["heart_rate","full","basic","duration"]) {
    const card=document.createElement("article");card.className=`benchmark-card${mode===$("mode").value ? " active" : ""}`;
    const title=document.createElement("h3");title.textContent=names[mode]+(mode===$("mode").value ? " · selected" : "");
    const value=document.createElement("strong");value.textContent=fmt(meta.systems[mode].test_mae,3);
    const text=document.createElement("p");text.textContent=`${meta.systems[mode].input_columns.length} input fields · interpreted kcal/session`;
    card.append(title,value,text);$("benchmark-cards").append(card);
  }
}
async function estimate(event) {
  if(event) event.preventDefault();
  if(!$("session").reportValidity()) return;
  clearResult(); const current=revision; pending=new AbortController();
  $("estimate").disabled=true; $("result-tag").textContent="Estimating…";
  const mode=$("mode").value, inputs={};
  for(const name of meta.systems[mode].input_columns) inputs[name]=values[name];
  try {
    const data=CalorieInference.predict(meta,forests,{mode,inputs});
    if(current!==revision) return;
    $("prediction").textContent=fmt(data.prediction);
    $("interval").textContent=`${fmt(data.lower)} – ${fmt(data.upper)}`;
    $("mae").textContent=`${fmt(data.test_mae,3)} kcal*`;
    $("coverage").textContent=`${fmt(data.test_coverage*100)}%`;
    const group=data.duration_group;
    $("duration-note").textContent=`For ${group.group} minute sessions, this model's test intervals covered ${fmt(group.coverage*100)}% of ${group.n.toLocaleString()} recorded labels. ${group.coverage<.9 ? "Coverage was below the 90% nominal target in this group." : "This group result is descriptive, not a personal guarantee."}`;
    $("negative-note").hidden=!data.negative_lower_bound;
    $("active-model").textContent=`Using ${names[mode]} · frozen XGBoost · ${data.input_fields.length} fields`;
    $("empty-result").hidden=true; $("result").hidden=false; $("result-tag").textContent="Frozen model";
  } catch(error) {
    if(error.name!=="AbortError" && current===revision) {$("form-error").textContent=error.message;$("form-error").hidden=false;$("result-tag").textContent="Check inputs";}
  } finally { if(current===revision) {pending=null;$("estimate").disabled=false;} }
}
async function init() {
  try {
    const bundle=await CalorieInference.loadBundle(); meta=bundle.meta; forests=bundle.forests;
    values={...meta.examples[0].values}; $("mode").value=meta.primary_mode;
    for(const example of meta.examples) {const button=document.createElement("button");button.type="button";button.textContent=example.label;button.addEventListener("click",()=>{values={...example.values};renderFields();estimate();});$("examples").append(button);}
    $("mode").addEventListener("change",renderFields);
    $("session").addEventListener("submit",estimate);
    renderFields(); $("connection").textContent="● Four frozen models ready · examples are fictional";
    await estimate();
  } catch(error) {$("connection").textContent=`Could not load models: ${error.message} Reload the page or try again later.`;$("connection").setAttribute("role","alert");}
}
init();
