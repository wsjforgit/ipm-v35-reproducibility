#!/usr/bin/env python3
"""Synthetic regression tests for the pre-registered PM2019 retrieval extension.
No official qrels, NCT clinical texts or downloaded snapshots are bundled.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"protocol"))
import importlib
ix=importlib.import_module("01_ingest_2019_snapshot")
ir=importlib.import_module("02_retrieve_sqlite_fts5")
ev=importlib.import_module("03_evaluate_new_retrieval")


class TestCorpusParsing(unittest.TestCase):
    def test_public_synthetic_trial_xml_fields(self):
        xml="""<clinical_study>
          <id_info><nct_id>NCT12345678</nct_id></id_info>
          <brief_title>Melanoma targeted medicine</brief_title>
          <condition>Melanoma</condition><condition>Neoplasm</condition>
          <brief_summary><textblock>Trial summary BRAF.</textblock></brief_summary>
          <detailed_description><textblock>Study data</textblock></detailed_description>
          <eligibility><criteria><textblock>BRAF V600E eligible</textblock></criteria></eligibility>
          </clinical_study>"""
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"fake.xml";f.write_text(xml)
            with f.open("rb") as stream:nct,raw,tag=ix.unpack(stream)
        self.assertEqual(nct,"NCT12345678")
        self.assertIn("Melanoma targeted medicine",raw)
        self.assertIn("condition Melanoma Neoplasm",tag)
        self.assertIn("eligibility BRAF V600E eligible",tag)

    def test_invalid_id_is_error(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"bad.xml";f.write_text("<clinical_study><brief_title>x</brief_title></clinical_study>")
            with f.open("rb") as stream:
                with self.assertRaises(ValueError):ix.unpack(stream)


class TestRetrieval(unittest.TestCase):
    def test_q0_q1_tokens_fixed(self):
        self.assertEqual(ir.token("Disease: melanoma, gene: BRAF (E586K)"),["disease","melanoma","gene","braf","e586k"])
        self.assertEqual(ir.fts_expr(["gene","braf"]),'"gene" OR "braf"')

    def test_40_topic_query_parsing(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"topics.xml"
            root=ET.Element("topics")
            for i in range(1,41):
                item=ET.SubElement(root,"topic",{"number":str(i)})
                ET.SubElement(item,"disease").text="melanoma"
                ET.SubElement(item,"gene").text="BRAF V600E"
                ET.SubElement(item,"demographic").text="64-year-old female"
            path.write_bytes(ET.tostring(root))
            items=ir.topics_load(path)
            self.assertEqual(len(items),40)
            self.assertIn("condition",items[0]["query_tokens"]["Q1"])
            self.assertNotIn("condition",items[0]["query_tokens"]["Q0"])

    def test_same_small_fts_population(self):
        db=sqlite3.connect(":memory:")
        db.execute("CREATE TABLE doc_map(rid INTEGER PRIMARY KEY, nctid TEXT UNIQUE)")
        for name in ("fts_raw","fts_label"):
            db.execute(f"CREATE VIRTUAL TABLE {name} USING fts5(body, tokenize='porter unicode61')")
        for i,(raw,tag) in enumerate([("melanoma trial eligibility BRAF","condition melanoma eligibility BRAF"),
                                      ("asthma trial","condition asthma eligibility")],1):
            db.execute("INSERT INTO doc_map(rid,nctid) VALUES (?,?)",(i,f"NCT{i:08d}"))
            db.execute("INSERT INTO fts_raw(rowid,body) VALUES (?,?)",(i,raw))
            db.execute("INSERT INTO fts_label(rowid,body) VALUES (?,?)",(i,tag))
        docs=ir.score(db,"fts_raw",'"melanoma"',1000)
        self.assertEqual([d["doc_id"] for d in docs],["NCT00000001"])
        self.assertEqual(ir.score(db,"fts_label",'"melanoma"',1000)[0]["doc_id"],"NCT00000001")
        db.close()

class TestMetrics(unittest.TestCase):
    def test_linear_discount(self):
        judged={"a":2,"b":1}
        self.assertAlmostEqual(ev.metric(judged,["a","b"],"linear"),1.)
        self.assertGreater(ev.metric(judged,["b","a"],"linear"),0.)
        self.assertLess(ev.metric(judged,["b","a"],"linear"),1.)
        self.assertNotEqual(ev.metric(judged,["b","a"],"exp2"),ev.metric(judged,["b","a"],"linear"))

    def test_interaction_formula(self):
        x={"G00":{"nDCG10_linear":.1},"G01":{"nDCG10_linear":.2},
           "G10":{"nDCG10_linear":.3},"G11":{"nDCG10_linear":.5}}
        self.assertAlmostEqual(ev.interaction(x,"nDCG10_linear"),.1)

    def test_eval_one_with_two_relevant(self):
        out=ev.eval_one({"NCT1":2,"NCT2":1},["NCT1","NCT3","NCT2"])
        self.assertAlmostEqual(out["P10"],.2)
        self.assertAlmostEqual(out["Recall100"],1.)
        self.assertEqual(out["judged_positive_count"],2)

    def test_grades_and_conflicting_judgments(self):
        with tempfile.TemporaryDirectory() as d:
            q=Path(d)/"qrels.txt";q.write_text("1 0 NCT1 2\n1 0 NCT2 1\n")
            self.assertEqual(ev.load_qrels(q)["1"]["NCT1"],2)
            q.write_text("1 0 NCT1 0\n1 0 NCT1 2\n")
            with self.assertRaises(ValueError):ev.load_qrels(q)

if __name__=="__main__":
    unittest.main()
