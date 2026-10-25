import sys, os
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    cmd = sys.argv[1]
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    if cmd == 'run':
        from ucert.run import main
    elif cmd == 'planted':
        from ucert.planted import main
    elif cmd == 'tierc':
        from ucert.tierc import main
    elif cmd == 'compare':
        from ucert.compare import main
    else:
        raise SystemExit('unknown subcommand ' + cmd)
    main()
