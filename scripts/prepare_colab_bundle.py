"""Prepare an uploadable snapshot and a personal Colab notebook; no training here.

Run from the repository: python scripts/prepare_colab_bundle.py
The supplied checks, tests, data, and training scripts are copied unchanged.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import textwrap
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work/colab"
NB_PATH = ROOT / "notebooks/day09_train_LuuNhatNam_03243.ipynb"


def digest(path):
    return hashlib.sha1(path.read_bytes()).hexdigest()


def cell(kind, source):
    result = {"cell_type": kind, "metadata": {},
              "source": textwrap.dedent(source).strip() + "\n"}
    if kind == "code":
        result.update(execution_count=None, outputs=[])
        compile(result["source"], "<colab-cell>", "exec")
    return result


def main():
    manifest_path = ROOT / "submission/export/clean_v1/manifest.json"
    summary = json.loads((ROOT / "submission/reports/08_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config_sha = digest(ROOT / "configs/pipeline.yaml")
    manifest_sha = digest(manifest_path)
    assert summary["config_sha1"] == config_sha, "Run the pipeline with the current config first"
    assert manifest["decision"] == summary["verdict"]
    assert manifest["decision"]["n_errors"] == 0
    for name in manifest["images"]:
        label = ROOT / "submission/export/clean_v1/labels" / Path(name).with_suffix(".txt").name
        assert digest(label)[:12] == manifest["label_sha1"][label.name], label

    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    paths = {Path(name) for name in tracked if name}
    for folder in ["submission/reports", "submission/calibration", "submission/export", "submission/evidence"]:
        paths.update(p.relative_to(ROOT) for p in (ROOT / folder).rglob("*") if p.is_file())
    paths.add(Path("scripts/prepare_colab_bundle.py"))
    paths.add(Path("docs/FINISH_LAB09.md"))
    paths = {p for p in paths if (ROOT / p).is_file()
             and not any(part in {".git", ".venv", "__pycache__", "_instructor", ".aws", ".codex", ".agents"} for part in p.parts)
             and p.suffix.lower() not in {".pt", ".pyc", ".pem", ".key"}
             and p.name != ".env"}
    assert Path("scripts/human_review_sim.py") in paths
    OUT.mkdir(parents=True, exist_ok=True)
    archive = OUT / "day09_colab_bundle.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(paths):
            z.write(ROOT / path, "day09_lab/" + path.as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()

    setup = f'''
import hashlib, json, os, pathlib, zipfile
from google.colab import files
EXPECTED_BUNDLE_SHA256 = {archive_sha!r}
EXPECTED_CONFIG_SHA1 = {config_sha!r}
EXPECTED_MANIFEST_SHA1 = {manifest_sha!r}
ROOT = pathlib.Path("/content/day09_lab")
if not (ROOT / "submission/export/clean_v1/manifest.json").exists():
    print("Chọn file day09_colab_bundle.zip đã chuẩn bị trên máy Windows.")
    uploaded = files.upload()
    assert len(uploaded) == 1, "Chỉ chọn một file ZIP dữ liệu."
    name, content = next(iter(uploaded.items()))
    assert hashlib.sha256(content).hexdigest() == EXPECTED_BUNDLE_SHA256, "Sai gói ZIP hoặc gói đã thay đổi."
    destination = pathlib.Path("/content").resolve()
    with zipfile.ZipFile(pathlib.Path(name)) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            assert target.is_relative_to(destination), "Đường dẫn ZIP không hợp lệ."
        archive.extractall(destination)
else:
    print("Dùng lại snapshot trong phiên Colab hiện tại.")
os.chdir(ROOT)
sha1 = lambda p: hashlib.sha1(pathlib.Path(p).read_bytes()).hexdigest()
assert sha1("configs/pipeline.yaml") == EXPECTED_CONFIG_SHA1, "Cấu hình khác snapshot."
assert sha1("submission/export/clean_v1/manifest.json") == EXPECTED_MANIFEST_SHA1, "Export khác snapshot."
manifest = json.loads(pathlib.Path("submission/export/clean_v1/manifest.json").read_text())
for image in manifest["images"]:
    label = pathlib.Path("submission/export/clean_v1/labels") / pathlib.Path(image).with_suffix(".txt").name
    assert sha1(label)[:12] == manifest["label_sha1"][label.name], str(label)
print("Clean:", manifest["n_images"], "ảnh | quyết định:", manifest["decision"]["decision"])
SEEDS, EPOCHS, VARIANTS = [0, 1], 20, ["raw", "clean"]
MODEL, BATCH, IMGSZ = "yolo26n.pt", 16, 640
'''
    cells = [
        cell("markdown", """
        # Day 09 — Luu Nhat Nam, 03243: raw vs clean

        **Trước khi chạy:** Runtime → Change runtime type → T4 GPU → Save.
        Chạy các ô theo thứ tự. Ô 1 yêu cầu upload `day09_colab_bundle.zip` từ máy Windows.

        Snapshot giữ dataset **Hold**, 202 ảnh clean; raw có 224 ảnh nguồn (Ultralytics có thể bỏ ảnh/nhãn hỏng).
        Cùng yolo26n, 20 epoch, batch 16, imgsz 640, seed 0 và 1; gold_val chỉ dùng val, test chỉ đo cuối.
        Gói giữ nguyên các script đề và dữ liệu, bao gồm dữ liệu phục vụ test người duyệt mô phỏng.
        Chỉ train hai biến thể raw/clean. Không đọc nhãn tham chiếu để tạo kết quả train.
        """),
        cell("code", setup),
        cell("markdown", "## 2. Cài đúng thư viện của lab"),
        cell("code", """
        import subprocess, sys
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements-train.txt"], check=True)
        import torch, ultralytics
        assert torch.cuda.is_available(), "Chưa có GPU: chọn Runtime → Change runtime type → T4 GPU."
        assert ultralytics.__version__ == "8.4.214", ultralytics.__version__
        print("GPU:", torch.cuda.get_device_name(0), "| ultralytics:", ultralytics.__version__)
        """),
        cell("markdown", "## 3. Kiểm tra phần lõi trên Linux (giữ nguyên bộ kiểm tra đề)"),
        cell("code", """
        evidence = pathlib.Path("submission/evidence")
        evidence.mkdir(parents=True, exist_ok=True)
        checked = subprocess.run([sys.executable, "scripts/check_submission.py", "--no-train"],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (evidence / "colab_check_core.log").write_text(checked.stdout, encoding="utf-8")
        print(checked.stdout)
        assert checked.returncode == 0, "Còn lỗi kiểm tra; gửi nội dung ô này trước khi train."
        """),
        cell("markdown", """
        ## 4. Train 4 lượt: raw seed 0/1, clean seed 0/1

        Có thể chạy lại ô này sau lỗi tạm thời: chỉ bỏ qua lượt đã có JSON khớp snapshot và cấu hình.
        Đọc cảnh báo Ultralytics về raw: số ảnh nguồn không nhất thiết bằng số ảnh thực tế được model nhận.
        Giữ tab Colab mở; thời gian phụ thuộc GPU được cấp. Không đổi tham số giữa các lượt.
        """),
        cell("code", """
        results = pathlib.Path("submission/results")
        results.mkdir(parents=True, exist_ok=True)
        for p in results.glob("*_seed*.json"):
            data = json.loads(p.read_text())
            assert data["variant"] in VARIANTS and data["seed"] in SEEDS, f"Kết quả ngoài thí nghiệm: {p}"
            for key, value in {"epochs": EPOCHS, "batch": BATCH, "imgsz": IMGSZ, "model": MODEL,
                               "config_sha1": EXPECTED_CONFIG_SHA1}.items():
                assert data.get(key) == value, f"Không trộn kết quả khác cấu hình: {p}, {key}"
            if data["variant"] == "clean":
                assert data["manifest_sha1"] == EXPECTED_MANIFEST_SHA1, f"Export khác: {p}"
        command = [sys.executable, "scripts/train_compare.py", "--variants", *VARIANTS,
                   "--seeds", *map(str, SEEDS), "--epochs", str(EPOCHS), "--batch", str(BATCH),
                   "--imgsz", str(IMGSZ), "--model", MODEL, "--device", "0", "--skip-existing"]
        print(" ".join(command))
        with (evidence / "colab_train.log").open("a", encoding="utf-8") as log:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, bufsize=1)
            for line in process.stdout:
                print(line, end="", flush=True)
                log.write(line)
                log.flush()
            return_code = process.wait()
        assert return_code == 0, "Train chưa xong. Gửi đoạn lỗi cuối; đừng tự tạo kết quả JSON."
        runtime = {"torch": torch.__version__, "ultralytics": ultralytics.__version__,
                   "gpu": torch.cuda.get_device_name(0), "config_sha1": EXPECTED_CONFIG_SHA1,
                   "manifest_sha1": EXPECTED_MANIFEST_SHA1, "clean_decision": manifest["decision"]["decision"]}
        (results / "colab_run_info.json").write_text(json.dumps(runtime, indent=2), encoding="utf-8")
        """),
        cell("markdown", "## 5. Tổng hợp bằng script đề, xem kết quả"),
        cell("code", """
        from IPython.display import display, Markdown, Image
        expected = {f"{variant}_seed{seed}.json" for variant in VARIANTS for seed in SEEDS}
        actual = {p.name for p in results.glob("*_seed*.json")}
        assert actual == expected, f"Chưa đủ đúng 4 kết quả: {actual}"
        subprocess.run([sys.executable, "scripts/summarize_results.py"], check=True)
        display(Markdown((results / "comparison.md").read_text()))
        if (results / "comparison.png").exists():
            display(Image(filename=str(results / "comparison.png")))
        print("Clean là bản Hold. Chỉ kết luận tốt hơn khi chênh lệch vượt độ nhiễu giữa seed.")
        """),
        cell("markdown", "## 6. Tải kết quả về máy, rồi gửi file ZIP cho Codex để hoàn thiện REPORT"),
        cell("code", """
        output = pathlib.Path("/content/day09_results_03243.zip")
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for p in sorted(results.iterdir()):
                if p.is_file() and p.name != ".gitkeep":
                    archive.write(p, p.as_posix())
            for name in ["colab_check_core.log", "colab_train.log"]:
                p = evidence / name
                if p.exists():
                    archive.write(p, p.as_posix())
        print("Tải", output.name, "và giữ bản notebook có output. Không tải trọng số .pt để commit.")
        files.download(str(output))
        """),
    ]
    notebook = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"name": NB_PATH.name},
                "kernelspec": {"display_name": "Python 3", "name": "python3"},
                "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 4}
    NB_PATH.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("Notebook:", NB_PATH)
    print("Upload ZIP:", archive, f"({archive.stat().st_size / 1024**2:.1f} MiB)")
    print("Bundle SHA256:", archive_sha)
    print("Files:", len(paths), "| clean images:", manifest["n_images"])


if __name__ == "__main__":
    main()
