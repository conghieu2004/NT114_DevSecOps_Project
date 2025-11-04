# Mục tiêu: tăng coverage bằng cách import toàn bộ các module để thực thi phần top-level.
import importlib


def test_import_all_modules_smoke():
    modules = [
        "app.config",
        "app.logger",
        "app.main",
        "app.models",
        "app.utils",
        "app.api.auth",
        "app.api.users",
    ]
    for m in modules:
        importlib.import_module(m)