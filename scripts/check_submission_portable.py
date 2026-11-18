"""Run the original submission checker with two explicit compatibility fixes.

Usage: python scripts/check_submission_portable.py [--no-train]

The supplied checker stays unchanged on disk. Its complete checks, protected
file hashes, tests, gates and training checks still run. The in-memory fixes:
1. Compare project paths using '/', as stored in _protected.json.
2. Hash manifest bytes exactly as train_compare.py does. Do not normalize CRLF
   for this comparison; the protected-file hash function is left unchanged.

This is a local compatibility runner, not the instructor's official checker.
If the original checker changes, stop instead of applying a guessed patch.
"""
from pathlib import Path


def main():
    original = Path(__file__).with_name("check_submission.py")
    source = original.read_text(encoding="utf-8")
    replacements = (
        (
            "if str(p.relative_to(ROOT)) not in prot",
            "if p.relative_to(ROOT).as_posix() not in prot",
        ),
        (
            'if r.get("manifest_sha1") != sha1(mf):',
            'if r.get("manifest_sha1") != hashlib.sha1(mf.read_bytes()).hexdigest():',
        ),
    )
    for before, after in replacements:
        if source.count(before) != 1:
            raise RuntimeError(
                "Bản checker đã thay đổi; không áp dụng bản vá tương thích. "
                f"Không tìm được duy nhất: {before}"
            )
        source = source.replace(before, after, 1)

    print("Kiểm tra đầy đủ bằng checker gốc + 2 sửa lỗi tương thích:", flush=True)
    print("- Đường dẫn so với danh sách bảo vệ: POSIX (/).", flush=True)
    print("- Hash manifest: byte gốc, khớp cách script train ghi nhận.", flush=True)
    print("Giữ nguyên file đề, JSON train và mọi điều kiện kiểm tra.", flush=True)
    namespace = {
        "__name__": "__main__",
        "__file__": str(original.resolve()),
        "__package__": None,
    }
    exec(compile(source, str(original), "exec"), namespace)


if __name__ == "__main__":
    main()
