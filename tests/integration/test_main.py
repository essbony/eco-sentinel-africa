from meta_ai_dev import main


def test_main(capsys):
    main()
    captured = capsys.readouterr()
    assert "Hello from" in captured.out
