"""WISPAR FLOW Launcher"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
os.chdir(os.path.dirname(__file__))

if __name__ == "__main__":
    from dictate import main
    main()
