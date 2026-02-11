"""Entry point for kakitui."""

from kakitui.app import KakiTUIApp


def main() -> None:
    """Run the kakitui application."""
    app = KakiTUIApp()
    app.run()


if __name__ == "__main__":
    main()
