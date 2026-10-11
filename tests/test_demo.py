"""Inference-only contracts, input validation and non-disclosure through HTTP."""

import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from calorie_estimation.demo_app import Demo


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.app=Demo.__new__(Demo)
        self.app.manifest={"fields":{"Duration":{"label":"Duration","unit":"minutes","min":1,"max":30,"integer":True},
            "Gender":{"label":"Recorded gender","categories":["female","male"]},
            "Heart_Rate":{"label":"Heart rate","unit":"bpm","min":67,"max":128,"integer":True}},
            "systems":{"duration":{"input_columns":["Duration"]},"heart_rate":{"input_columns":["Duration","Gender","Heart_Rate"]}}}

    def request(self,path,method='GET',body=None,**extra):
        captured=[]
        content=json.dumps(body).encode() if body is not None else b''
        environ={"PATH_INFO":path,"REQUEST_METHOD":method,"CONTENT_TYPE":"application/json",
            "CONTENT_LENGTH":str(len(content)),"wsgi.input":io.BytesIO(content),"HTTP_HOST":"localhost:7860",**extra}
        output=b''.join(self.app(environ,lambda status,headers:captured.append((status,dict(headers)))))
        return captured[0][0],captured[0][1],output

    def test_missing_sensor_is_rejected_instead_of_filled(self):
        with self.assertRaisesRegex(ValueError,'exactly'):
            self.app.validate({"mode":"heart_rate","inputs":{"Duration":15,"Gender":"female"}})
        self.assertEqual(self.app.validate({"mode":"duration","inputs":{"Duration":15}}),('duration',{'Duration':15}))

    def test_unused_sensor_and_unknown_mode_are_rejected(self):
        for payload in ({"mode":"duration","inputs":{"Duration":15,"Heart_Rate":98}},
                        {"mode":"anything","inputs":{}},{"mode":[],"inputs":{}},[]):
            with self.subTest(payload=payload),self.assertRaises(ValueError):
                self.app.validate(payload)

    def test_invalid_numbers_and_extrapolation_are_rejected(self):
        for value in (None,True,float('nan'),float('inf'),0,31,1.5,"15"):
            with self.subTest(value=value),self.assertRaises(ValueError):
                self.app.validate({"mode":"duration","inputs":{"Duration":value}})
        for value in (1,30):
            self.app.validate({"mode":"duration","inputs":{"Duration":value}})

    def test_unknown_categories_are_not_silently_encoded(self):
        for value in ("unknown","FEMALE",[],None):
            with self.subTest(value=value),self.assertRaises(ValueError):
                self.app.validate({"mode":"heart_rate","inputs":{"Duration":15,"Gender":value,"Heart_Rate":98}})

    def test_cross_origin_post_is_rejected_before_prediction(self):
        status,_,_=self.request('/api/predict','POST',{},HTTP_ORIGIN='https://unrelated.example')
        self.assertEqual(status,'403 Forbidden')

    def test_body_size_and_content_type_are_bounded(self):
        for length in ('0','-1','8193'):
            status,_,_=self.request('/api/predict','POST',{},CONTENT_LENGTH=length)
            self.assertEqual(status,'413 Content Too Large')
        self.assertEqual(self.request('/api/predict','POST',{},CONTENT_TYPE='text/plain')[0],'415 Unsupported Media Type')

    def test_artifacts_and_arbitrary_paths_are_not_served(self):
        for path in ('/bundle/xgboost_full.joblib','/../requirements.txt','/runs/final-test-access.json'):
            self.assertEqual(self.request(path)[0],'404 Not Found')
        status,headers,_=self.request('/missing')
        self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertIn("script-src 'self'",headers['Content-Security-Policy'])

    def test_corrupt_artifact_is_rejected_before_deserialization(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)
            (folder/'bad.joblib').write_bytes(b'not a model')
            manifest={"systems":{"duration":{"artifact":"bad.joblib","model_sha256":"wrong"}}}
            (folder/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                Demo(folder,folder)


if __name__=='__main__':
    unittest.main()
