#!/usr/bin/env python3
import sys


def main():
    if "--cli" in sys.argv:
        # Remove the flag and delegate to CLI
        sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:] if a != "--cli"]
        from verdant import main as cli_main
        return cli_main()
    else:
        # Default to GUI
        import verdant_gui  # will run its own main
        return verdant_gui.main()


if __name__ == "__main__":
    main() 