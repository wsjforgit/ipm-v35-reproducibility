#!/usr/bin/env python3
"""Build a local SQLite-FTS5 index for the ORIGINAL 2019 TREC-PM trial snapshot.

Uses only stdlib sqlite3, tarfile, ElementTree. Preserves the 2019 trial
document content as private, unpublishable research input. Does not open qrels.

Index representation R0: raw concatenation of title/condition/summary/
description/eligibility. R1: same contents with fixed field-name prefixes.
The document universe is identical in both tables; no relevance data consulted.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tarfile
import time
import xml.etree.ElementTree as ET

EXPECTED = [277495873,266267182,242899908,218698307]
VERSION = "trec-pm2019-sqlite-fts5-dual-representation-v1"

def vals(root, expr):
    return [" ".join((x.text or "").split()) for x in root.findall(expr) if (x.text or "").strip()]

def text(root, expr):
    el=root.find(expr)
    return " ".join("".join(el.itertext()).split()) if el is not None else ""

def unpack(fileobj):
    root=ET.parse(fileobj).getroot()
    nct=text(root, "id_info/nct_id")
    if not nct.startswith("NCT"):
        raise ValueError("Invalid 2019 NCT trial identifier")
    title=text(root,"brief_title")+" "+text(root,"official_title")
    title=" ".join(title.split())
    conditions=" ".join(vals(root,"condition"))
    summary=text(root,"brief_summary/textblock")
    detail=text(root,"detailed_description/textblock")
    criteria=text(root,"eligibility/criteria/textblock")
    fields=[title,conditions,summary,detail,criteria]
    # EXACT SAME source words, only labels added in the field representation.
    raw=" ".join(s for s in fields if s).strip()
    labelled=" ".join(
        f"{key} {value}" for key,value in zip(
            ("title","condition","summary","description","eligibility"), fields
        ) if value
    ).strip()
    if not raw:
        raise ValueError("No indexed text for original trial "+nct)
    return nct,raw,labelled

def init_db(db):
    c=sqlite3.connect(str(db),timeout=80)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    c.execute("PRAGMA cache_size=-64000")
    c.execute("CREATE TABLE IF NOT EXISTS doc_map(rid INTEGER PRIMARY KEY, nctid TEXT NOT NULL UNIQUE)")
    c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts_raw USING fts5(body, tokenize='porter unicode61')")
    c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts_label USING fts5(body, tokenize='porter unicode61')")
    c.commit()
    return c

def run(args):
    dest=Path(args.output_dir)
    dest.mkdir(parents=True,exist_ok=True)
    db=dest/("pilot_fts.sqlite" if args.pilot else "official_2019_snapshot_full_fts.sqlite")
    checkpoint=dest/("pilot_index_receipt.json" if args.pilot else "full_index_receipt.json")
    if checkpoint.exists() and not args.pilot:
        old=json.loads(checkpoint.read_text())
        if old.get("complete"):
            print(json.dumps({"already_completed_receipt":str(checkpoint),
                              "docs":old["indexed_unique_trials"]}),flush=True)
            return
    conn=init_db(db)
    scanned=0;inserted=0;dup=0;failed=0
    per_part=[]
    started=time.time()
    for part in range(4):
        archive=Path(args.corpus_dir)/f"clinical_trials.{part}.tar.gz"
        if not archive.exists() or archive.stat().st_size!=EXPECTED[part]:
            raise RuntimeError("Missing official snapshot part or wrong bytes: "+str(archive))
        p_scan=0;p_insert=0;p_dup=0
        with tarfile.open(str(archive),mode="r|gz") as tar:
            conn.execute("BEGIN")
            for member in tar:
                if not member.isfile() or not member.name.endswith(".xml"):
                    continue
                fileobj=tar.extractfile(member)
                if fileobj is None:raise RuntimeError("Bad tar member "+member.name)
                nct,raw,structured=unpack(fileobj)
                p_scan+=1;scanned+=1
                try:
                    row=conn.execute("INSERT INTO doc_map(nctid) VALUES (?)",(nct,))
                    rid=row.lastrowid
                except sqlite3.IntegrityError:
                    p_dup+=1;dup+=1
                    continue
                conn.execute("INSERT INTO fts_raw(rowid,body) VALUES (?,?)",(rid,raw))
                conn.execute("INSERT INTO fts_label(rowid,body) VALUES (?,?)",(rid,structured))
                p_insert+=1;inserted+=1
                if p_scan%2000==0:
                    conn.commit();conn.execute("BEGIN")
                if p_scan%12000==0:
                    print(json.dumps({"part":part,"docs_seen_this_part":p_scan,
                        "inserted_this_part":p_insert,"elapsed_sec":int(time.time()-started)},
                        ensure_ascii=False),flush=True)
                if args.pilot and scanned>=args.pilot:
                    break
            conn.commit()
        per_part.append({"part":part,"scanned":p_scan,"inserted":p_insert,"duplicates":p_dup})
        print(json.dumps({"part_completed":part,"count":p_scan,
                          "inserted":p_insert,"seconds_elapsed":int(time.time()-started)}),
              flush=True)
        if args.pilot and scanned>=args.pilot:
            break
    total=conn.execute("SELECT COUNT(*) FROM doc_map").fetchone()[0]
    for table in ("fts_raw","fts_label"):
        count=conn.execute("SELECT COUNT(*) FROM "+table).fetchone()[0]
        if count!=total:
            raise ValueError(f"{table} contains {count}, doc_map {total}!")
    if not args.pilot and total!=306238:
        raise ValueError("Unexpected official clinicaltrials/2019 corpus size: "+str(total))
    conn.close()
    receipt={"version":VERSION,"pilot":bool(args.pilot),"complete":True,
        "2019_source_only":True,"no_qrels_used_in_index":True,
        "indexed_unique_trials":total,"documents_scanned_this_run":scanned,
        "new_insertions_this_run":inserted,"duplicate_trials_skipped":dup,
        "parts":per_part,"sqlite_file":db.name,"sqlite_bytes":db.stat().st_size,
        "seconds_elapsed":round(time.time()-started,2),
        "source_compressed_parts_sha256":{}}
    if not args.pilot:
        for part in range(4):
            f=Path(args.corpus_dir)/f"clinical_trials.{part}.tar.gz"
            h=hashlib.sha256()
            with f.open("rb") as stream:
                for buf in iter(lambda:stream.read(1<<20),b""):
                    h.update(buf)
            receipt["source_compressed_parts_sha256"][f.name]=h.hexdigest()
    checkpoint.write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print("INDEX_COMPLETE "+json.dumps({
        "pilot":receipt["pilot"],"documents":total,"seconds":receipt["seconds_elapsed"],
        "db_gb":round(db.stat().st_size/1e9,3)},ensure_ascii=False),flush=True)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--corpus-dir",required=True)
    ap.add_argument("--output-dir",required=True)
    ap.add_argument("--pilot",type=int,default=0,help="For index-only smoke test, no qrels.")
    run(ap.parse_args())
