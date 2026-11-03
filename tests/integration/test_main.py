from eco_sentinel.main import main


def test_main(capsys):
    main()
    captured = capsys.readouterr()
    assert "Eco Sentinel Africa" in captured.out


def test_main_compat(capsys):
    """Compat — l'ancien import doit toujours fonctionner."""
    from meta_ai_dev import main as compat_main

    compat_main()
    captured = capsys.readouterr()
    assert "Eco Sentinel Africa" in captured.out
