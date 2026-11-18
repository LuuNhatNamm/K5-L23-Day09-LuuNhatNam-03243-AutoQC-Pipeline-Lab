"""CHECK 6 — Ý kiến thứ hai: so nhãn với một model LỚN HƠN (yolo26l).   ★★★ (khó nhất, đáng điểm nhất)

Test:  pytest tests/test_second_opinion.py -q

Máy kiểm quy tắc, người kiểm ý nghĩa (slide). Các lỗi như thiếu nhãn / gán nhầm lớp hợp lệ / box lỏng
KHÔNG bắt được bằng quy tắc cú pháp. Ta nhờ một model mạnh hơn "nhìn lại" và CHỈ CẢNH BÁO (model cũng có thể sai):
những ảnh bị cờ sẽ vào hàng đợi cho NGƯỜI duyệt.

`preds[stem]` = list `[id_lớp, conf, cx, cy, w, h]` của model (lấy qua `get_preds(ds, cfg, "checker")` nếu preds=None).
`L = ds.valid_boxes(stem)` = list `(id_lớp, cx, cy, w, h)` của nhãn (đã bỏ dòng hỏng).
Ngưỡng ở `cfg["second_opinion"]`: conf, min_area_px, fp_conf, iou_missing, iou_match, iou_loose.

Thuật toán gợi ý, với từng ảnh (bỏ qua ảnh không có trong preds hoặc không có file nhãn):
  P = dự đoán có conf >= conf  VÀ diện tích px (w*W * h*H) >= min_area_px
  Với mỗi dự đoán r trong P: lấy các nhãn có IoU(r, nhãn) >= iou_missing  (cands)
   - không có cands                            -> POSSIBLE_MISSING     (model thấy vật mà nhãn không có box)
   - có cands cùng lớp, tốt nhất IoU < iou_loose -> POSSIBLE_LOOSE_BOX  (đúng vật, box lỏng/lệch)
   - không có cands cùng lớp, nhưng cands tốt nhất IoU >= iou_match (khác lớp) -> POSSIBLE_WRONG_CLASS
  Với mỗi dòng nhãn hợp lệ: nếu IoU với MỌI dự đoán (conf >= fp_conf, không lọc diện tích) đều < iou_missing
                                             -> POSSIBLE_FALSE_POS  (box nhãn không khớp vật nào model thấy; Issue.line = số dòng)

Chi tiết các ca biên (test kiểm đúng các ca này)
- `cands` gồm nhãn MỌI lớp có IoU >= iou_missing; "tốt nhất cùng lớp" = cands cùng lớp có IoU lớn nhất; "tốt nhất khác lớp" tương tự với cands khác lớp.
- Thứ tự quyết định cho mỗi dự đoán: (1) cands rỗng -> MISSING. (2) có cands cùng lớp: IoU tốt nhất < iou_loose -> LOOSE_BOX, ngược lại KHÔNG cờ
  (nhãn đúng lớp đã phủ vật này, kể cả khi còn nhãn khác lớp chồng lên). (3) không có cands cùng lớp: nếu IoU tốt nhất khác lớp >= iou_match -> WRONG_CLASS;
  nếu chỉ có khác lớp với IoU trong [iou_missing, iou_match) -> không cờ gì (mơ hồ: để cho FALSE_POS / lần duyệt khác).
- Một dự đoán sinh tối đa MỘT issue (MISSING / LOOSE_BOX / WRONG_CLASS); một ảnh có thể có nhiều issue.
- Thứ tự issue: theo `ds.image_files()` rồi theo thứ tự dự đoán trong `preds[stem]`, cuối cùng là các FALSE_POS theo số dòng; `Issue.image` = stem, `Issue.line` chỉ đặt cho FALSE_POS.

Lưu ý số dòng: dùng `ds.read_label_lines(stem)` (giữ số dòng gốc, kể cả dòng hỏng/trống) để lấy `Issue.line`; `valid_boxes` KHÔNG giữ số dòng.

Tất cả severity WARN; `Issue.extra` nên có {"conf": ...} hoặc {"iou": ...} (hàng đợi duyệt dùng conf để xếp ưu tiên).

Gợi ý
- `iou_xywh` có sẵn. Dòng nhãn hỏng không được làm script chết (dùng `ds.valid_boxes` và `parse_yolo_line` trong try).
- Kết quả phụ thuộc mạnh vào ngưỡng: calibrate chúng ở Bước 3 thay vì đoán.
"""
from ..common import WARN, Issue, iou_xywh, parse_yolo_line  # noqa: F401
from ..model_cache import get_preds  # noqa: F401


def run(ds, cfg, preds=None):
    if preds is None:
        preds = get_preds(ds, cfg, "checker")

    limits = cfg["second_opinion"]
    issues = []

    for image_path in ds.image_files():
        stem = image_path.stem
        lines = ds.read_label_lines(stem)

        # Không có file nhãn hoặc không có dữ liệu dự đoán thì bỏ qua.
        if lines is None or stem not in preds:
            continue

        size = ds.image_size(stem)
        if size is None:
            continue
        width, height = size

        # Giữ số dòng gốc để báo lỗi chính xác.
        labels = []
        for line_no, text in lines:
            try:
                class_id, cx, cy, w, h = parse_yolo_line(text)
            except (ValueError, OverflowError):
                continue

            if not 0 <= class_id < len(ds.classes):
                continue
            if w <= 0 or h <= 0:
                continue

            labels.append((line_no, class_id, (cx, cy, w, h)))

        predictions = preds[stem]

        def report(code, message, line=None, extra=None):
            issues.append(
                Issue(
                    check="second_opinion",
                    severity=WARN,
                    code=code,
                    image=stem,
                    message=message,
                    line=line,
                    extra=extra or {},
                )
            )

        # 1. So từng dự đoán đáng tin với nhãn hiện có.
        for prediction in predictions:
            pred_class, confidence, cx, cy, w, h = prediction
            area_px = w * width * h * height

            if confidence < limits["conf"]:
                continue
            if area_px < limits["min_area_px"]:
                continue

            pred_box = (cx, cy, w, h)
            candidates = []

            for _, label_class, label_box in labels:
                overlap = iou_xywh(pred_box, label_box)
                if overlap >= limits["iou_missing"]:
                    candidates.append((label_class, overlap))

            if not candidates:
                report(
                    "POSSIBLE_MISSING",
                    "Model thấy đối tượng nhưng không có box nhãn khớp",
                    extra={"conf": confidence},
                )
                continue

            same_class = [
                overlap
                for label_class, overlap in candidates
                if label_class == pred_class
            ]

            # Ưu tiên nhãn cùng lớp nếu đã phủ đối tượng.
            if same_class:
                best_iou = max(same_class)
                if best_iou < limits["iou_loose"]:
                    report(
                        "POSSIBLE_LOOSE_BOX",
                        "Nhãn cùng lớp nhưng box có thể lỏng hoặc lệch",
                        extra={"conf": confidence, "iou": best_iou},
                    )
                continue

            best_iou = max(overlap for _, overlap in candidates)
            if best_iou >= limits["iou_match"]:
                report(
                    "POSSIBLE_WRONG_CLASS",
                    "Box khớp vị trí nhưng lớp khác dự đoán của model",
                    extra={"conf": confidence, "iou": best_iou},
                )

        # 2. Kiểm tra nhãn có được dự đoán nào hỗ trợ không.
        # Dùng fp_conf riêng và KHÔNG lọc diện tích dự đoán.
        fp_predictions = [
            prediction
            for prediction in predictions
            if prediction[1] >= limits["fp_conf"]
        ]

        for line_no, _, label_box in labels:
            best_iou = max(
                (
                    iou_xywh(label_box, prediction[2:])
                    for prediction in fp_predictions
                ),
                default=0.0,
            )

            if best_iou < limits["iou_missing"]:
                report(
                    "POSSIBLE_FALSE_POS",
                    "Box nhãn không khớp dự đoán nào đủ confidence",
                    line=line_no,
                    extra={"iou": best_iou},
                )

    return issues
