"""
Launcher script for Robot Drawing System.

This module provides a smart launcher that allows users to choose between
the graphical user interface and command-line interface based on their
preferences and available dependencies.

Features:
- Automatic dependency checking
- Interface selection menu
- Graceful fallback options
- User-friendly error handling
- Version information display

The launcher ensures users can always access the system functionality
regardless of their Python environment setup.

Author: Robot Drawing System
Version: 1.0
"""
import sys
import os

def show_menu():
    """
    Display the main launcher menu with available options.
    
    Shows system information, features, and interface choices.
    """
    print("=" * 50)
    print("      ROBOT DRAWING SYSTEM v1.0")
    print("=" * 50)
    print()
    print("Features:")
    print("• Optimized Edge Following (Fast & Accurate)")
    print("• TSP Path Optimization")
    print("• Real-time preview and visualization")
    print("• Robot communication and control")
    print("• Multiple precision levels")
    print("• Interactive drawing canvas")
    print()
    print("Choose your interface:")
    print("1. GUI Application (Recommended)")
    print("2. Command Line Interface")
    print("3. Exit")
    print()

def check_gui_dependencies():
    """Check if GUI dependencies are available"""
    try:
        import tkinter
        import PIL
        import matplotlib
        return True
    except ImportError as e:
        print(f"GUI dependencies missing: {e}")
        print("Please install required packages:")
        print("pip install pillow matplotlib")
        return False

def main():
    """Main launcher function"""
    while True:
        show_menu()
        
        try:
            choice = input("Enter your choice (1-3): ").strip()
            
            if choice == "1":
                # Launch GUI
                if check_gui_dependencies():
                    print("Starting GUI application...")
                    try:
                        from simple_gui import main as gui_main
                        gui_main()
                    except Exception as e:
                        print(f"Error starting GUI: {e}")
                        print("Falling back to command line interface...")
                        input("Press Enter to continue...")
                        from cli import main as cli_main
                        cli_main()
                else:
                    print("GUI not available. Starting command line interface...")
                    input("Press Enter to continue...")
                    from cli import main as cli_main
                    cli_main()
                break
                
            elif choice == "2":
                # Launch CLI
                print("Starting command line interface...")
                from cli import main as cli_main
                cli_main()
                break
                
            elif choice == "3":
                print("Goodbye!")
                sys.exit(0)
                
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
                input("Press Enter to continue...")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            input("Press Enter to continue...")

if __name__ == "__main__":
    main()
