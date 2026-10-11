"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const engine = require("../demo/static/engine.js");
const meta = {fields:{Duration:{label:"Duration",min:1,max:30,integer:true},Gender:{label:"Gender",categories:["female","male"]}},
  systems:{basic:{input_columns:["Duration","Gender"]}}};
const valid = {mode:"basic",inputs:{Duration:15,Gender:"female"}};
test("invalid payloads cannot silently substitute, coerce or extrapolate inputs", () => {
  for (const payload of [null,[],{...valid,extra:0},{...valid,mode:"toString"},
    {...valid,inputs:{Duration:15}}, {...valid,inputs:{...valid.inputs,Body_Temp:0}},
    ...[true,NaN,Infinity,"15",1.5,0,31].map(Duration=>({...valid,inputs:{...valid.inputs,Duration}})),
    {...valid,inputs:{...valid.inputs,Gender:"other"}}]) assert.throws(()=>engine.validate(meta,payload));
  assert.deepEqual(engine.validate(meta,valid),valid);
  assert.doesNotThrow(()=>engine.validate(meta,{...valid,inputs:{Duration:30,Gender:"male"}}));
});
test("float32 split equality follows the right branch; one-hot encoding preserves order", () => {
  const forest={format:"calorie-lab-scalar-gbtree-v1",features:[{name:"Duration"},{name:"Gender",category:"male"}],base_score:0,
    trees:[{left:[1,-1,-1],right:[2,-1,-1],feature:[0,0,0],value:[15,2,5]},
           {left:[1,-1,-1],right:[2,-1,-1],feature:[1,0,0],value:[.5,10,20]}]};
  assert.equal(engine.predictForest(forest,{Duration:14,Gender:"female"}),12);
  assert.equal(engine.predictForest(forest,{Duration:15,Gender:"male"}),25);
  assert.equal(engine.predictForest(forest,{Duration:15-1e-8,Gender:"male"}),25);
});
test("sequential accumulation rounds at each tree", () => {
  const leaf=value=>({left:[-1],right:[-1],feature:[0],value:[value]});
  const forest={format:"calorie-lab-scalar-gbtree-v1",features:[],base_score:16777216,trees:[leaf(1),leaf(-16777216)]};
  assert.equal(engine.predictForest(forest,{}),0);
});
test("asset integrity is checked before parsing or making predictions", async () => {
  const original=global.fetch;
  global.fetch=async url=>url==="./metadata.json" ? {ok:true,json:async()=>({systems:{basic:{browser_artifact:"models/basic.json",browser_sha256:"0".repeat(64)}}})}
    : {ok:true,arrayBuffer:async()=>new TextEncoder().encode("corrupt model").buffer};
  try {await assert.rejects(engine.loadBundle(),/integrity check failed/);} finally {global.fetch=original;}
});
