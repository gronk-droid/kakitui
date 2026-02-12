"""Entry point for kakitui."""

# Import before app runs so terminal capability detection doesn't run mid-session
import textual_image.widget  # noqa: F401

from kakitui.app import KakiTUIApp


def main() -> None:
    """Run the kakitui application."""
    app = KakiTUIApp()
    app.run()


if __name__ == "__main__":
    main()
