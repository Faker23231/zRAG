def main() -> None:
    """`kb-0716` 命令入口：启动统一 Web 服务。"""
    from zzk.web.app import main as run_web

    run_web()
