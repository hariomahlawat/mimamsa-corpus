"""Bind targeted Word reconstructions to searchable-text and image-render evidence."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import pymupdf


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""): digest.update(block)
    return digest.hexdigest()


def assessment(source_images,pdf_images,text_chars):
    if source_images and not pdf_images:return "HELD_IMAGE_EVIDENCE_NOT_RECOVERED"
    if source_images:return "RENDERED_IMAGE_EVIDENCE_MANUAL_FIDELITY_REVIEW_REQUIRED"
    if text_chars:return "SEARCHABLE_NATIVE_TEXT_REPRESENTATION"
    return "HELD_UNSEARCHABLE_RECONSTRUCTION"


def inspect_pdf(path,render_root,source_sha256,max_renders=3):
    document=pymupdf.open(path);text_chars=0;image_occurrences=0;renders=[]
    try:
        for number,page in enumerate(document,1):
            text_chars+=len(page.get_text("text"));images=page.get_images(full=True);image_occurrences+=len(images)
            if images and len(renders)<max_renders:
                destination=Path(render_root)/source_sha256[:2]/f"{source_sha256}-page-{number}.png"
                destination.parent.mkdir(parents=True,exist_ok=True)
                page.get_pixmap(dpi=120,alpha=False).save(destination)
                renders.append(destination.relative_to(Path(render_root).parent).as_posix())
        return {"pdf_pages":len(document),"pdf_text_characters":text_chars,
                "pdf_image_occurrences":image_occurrences,"visual_review_renders":renders}
    finally:document.close()


def run(args):
    inventory={row["sha256"]:row for row in load_jsonl(args.inventory)}
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True);rows=[]
    for item in load_jsonl(args.manifest):
        if item.get("status")!="CONVERTED_LOCAL_RECONSTRUCTION":continue
        source=inventory[item["source_sha256"]];pdf=Path(args.pdf_root)/Path(item["pdf_relative_path"]).name
        if sha256(pdf)!=item["pdf_sha256"]:raise ValueError(f"PDF hash mismatch: {pdf}")
        evidence=inspect_pdf(pdf,output/"visual-checks",item["source_sha256"])
        evidence.update({"inventory_id":item["inventory_id"],"relative_path":item["relative_path"],
                         "source_sha256":item["source_sha256"],"pdf_sha256":item["pdf_sha256"],
                         "source_embedded_image_count":source.get("embedded_image_count",0)})
        evidence["assessment"]=assessment(evidence["source_embedded_image_count"],
                                           evidence["pdf_image_occurrences"],evidence["pdf_text_characters"])
        rows.append(evidence)
    register=output/"CONVERSION_EVIDENCE_REGISTER.jsonl"
    register.write_text("".join(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n" for r in rows),encoding="utf-8")
    summary={"documents":len(rows),"image_documents":sum(r["source_embedded_image_count"]>0 for r in rows),
             "rendered_pages":sum(len(r["visual_review_renders"]) for r in rows),
             "held_image_evidence":sum(r["assessment"]=="HELD_IMAGE_EVIDENCE_NOT_RECOVERED" for r in rows),
             "manual_fidelity_review_required":sum("MANUAL_FIDELITY" in r["assessment"] for r in rows),
             "searchable":sum(r["pdf_text_characters"]>0 for r in rows)}
    (output/"CONVERSION_EVIDENCE_SUMMARY.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    return 1 if summary["held_image_evidence"] else 0


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory",required=True);parser.add_argument("--manifest",required=True)
    parser.add_argument("--pdf-root",required=True);parser.add_argument("--output",required=True)
    return run(parser.parse_args(argv))


if __name__=="__main__":raise SystemExit(main())
