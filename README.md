# ipy-auditlog

IPython のイベントフックを使い、コードセルの実行履歴を JSON Lines 形式で記録する軽量パッケージです。

## 使い方

Jupyter Notebook / JupyterLab / IPython で extension を読み込み、ログ収集を開始します。

```python
%load_ext ipy_auditlog
%auditlog_start
```

ファイル名には現在日時が自動で使われ、実行したセルは
`.jupyter_audit/` 配下の JSON Lines ファイルに記録されます。
状態の確認と停止は次のコマンドで行います。

```text
%auditlog_status
%auditlog_stop
```

ファイル名の指定、保存先、記録内容などのオプションは help を参照してください。

```text
%auditlog_start --help
```

## インストール

`pip`:

```bash
pip install ipy-auditlog
```

`uv` プロジェクト:

```bash
uv add ipy-auditlog
```

## ログ仕様（最小）

- 形式: JSON Lines（1イベント1行）
- 文字コード: UTF-8
- 拡張子: `.jsonl`
- デフォルトの出力ディレクトリ: `.jupyter_audit/`
- 既存ファイルがある場合は追記

イベント種別:

- `audit_started`
- `cell_executed`
- `audit_stopped`

### `cell_executed` の記録項目

- `started_at`
- `ended_at`
- `elapsed_sec`
- `status`（`success` / `failed`）
- `execution_count`
- `code`
- `output`（`--output` 指定時。JSON 化できない値は `repr()` の文字列）
- `error`（デフォルトで記録。失敗時は type / message / traceback）

## 開発

このリポジトリを editable install します。

```bash
python -m pip install -e .
```

`uv` を使用する場合:

```bash
uv pip install -e .
```

テストを実行します。

```bash
uv run pytest
```
