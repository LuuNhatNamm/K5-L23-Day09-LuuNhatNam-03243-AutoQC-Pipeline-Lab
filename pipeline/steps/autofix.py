"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict  # noqa: F401

import yaml  # noqa: F401

from ..common import ERROR, parse_yolo_line  # noqa: F401


def fix(ds, issues, cfg):
    fixes = []
    errors = [issue for issue in issues if issue.severity == ERROR]

    def record(image, line, action, before, after):
        fixes.append({
            "image": image,
            "line": line,
            "action": action,
            "before": before,
            "after": after,
        })

    # 1. Xóa ảnh không đạt và nhãn đi kèm trước.
    remove_codes = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}
    removed = {
        issue.image
        for issue in errors
        if issue.code in remove_codes
        or issue.code.startswith("DUP_IMAGE_")
    }

    for stem in sorted(removed):
        paths = [p for p in ds.image_files() if p.stem == stem]
        label_path = ds.label_path(stem)
        if label_path.exists():
            paths.append(label_path)

        if paths:
            before = "; ".join(str(p) for p in paths)
            for path in paths:
                path.unlink()
            ds._size_cache.pop(stem, None)
            record(stem, None, "remove_image", before, "(đã xóa)")

    # 2. Chuẩn hóa tên lớp trong data.yaml, giữ các mục khác.
    if any(issue.code == "BAD_CLASS_NAME" for issue in errors):
        data = (
            yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8"))
            if ds.yaml_path.exists()
            else {}
        ) or {}

        before = data.get("names")
        expected = dict(enumerate(cfg["classes"]))

        if ds.yaml_names() != expected:
            data["names"] = list(cfg["classes"])
            ds.yaml_path.write_text(
                yaml.safe_dump(
                    data, allow_unicode=True, sort_keys=False
                ),
                encoding="utf-8",
            )
            record(
                "data.yaml", None, "rename_classes",
                str(before), str(data["names"]),
            )

    # 3. Thiếu nhãn: chỉ ghi yêu cầu chuyển người gán.
    missing = {
        issue.image
        for issue in errors
        if issue.code == "MISSING_LABEL_FILE"
    }

    for stem in sorted(missing - removed):
        if ds.image_path(stem) is not None:
            if not ds.label_path(stem).exists():
                record(
                    stem, None, "needs_label",
                    "(không có file)", "chuyển người gán",
                )

    # 4. Gom lỗi theo ảnh và số dòng GỐC.
    grouped = defaultdict(lambda: defaultdict(set))
    drop_codes = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}

    for issue in errors:
        if issue.image in removed or issue.line is None:
            continue
        if issue.code in drop_codes or issue.code == "BOX_OUT_OF_IMAGE":
            grouped[issue.image][issue.line].add(issue.code)

    # 5. Mỗi file chỉ ghi lại một lần sau khi xử lý các dòng.
    for stem in sorted(grouped):
        path = ds.label_path(stem)
        if not path.exists():
            continue

        original = path.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
        output = []
        changed = False

        for line_no, text in enumerate(original, start=1):
            codes = grouped[stem].get(line_no, set())

            # Xóa dòng được ưu tiên hơn cắt box.
            if codes & drop_codes:
                record(stem, line_no, "drop_line", text, "")
                changed = True
                continue

            if "BOX_OUT_OF_IMAGE" in codes:
                try:
                    class_id, cx, cy, w, h = parse_yolo_line(text)
                except (ValueError, OverflowError):
                    record(stem, line_no, "drop_line", text, "")
                    changed = True
                    continue

                left = max(0.0, min(1.0, cx - w / 2))
                right = max(0.0, min(1.0, cx + w / 2))
                top = max(0.0, min(1.0, cy - h / 2))
                bottom = max(0.0, min(1.0, cy + h / 2))

                if right <= left or bottom <= top:
                    record(stem, line_no, "drop_line", text, "")
                    changed = True
                    continue

                new_box = (
                    (left + right) / 2,
                    (top + bottom) / 2,
                    right - left,
                    bottom - top,
                )

                # Chỉ ghi log nếu hình học thực sự thay đổi.
                if new_box != (cx, cy, w, h):
                    after = (
                        f"{class_id} "
                        + " ".join(f"{value:.12g}" for value in new_box)
                    )
                    record(stem, line_no, "clip_box", text, after)
                    output.append(after)
                    changed = True
                    continue

            output.append(text)

        if changed:
            path.write_text(
                "\n".join(output) + ("\n" if output else ""),
                encoding="utf-8",
            )

    return fixes