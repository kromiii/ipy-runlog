# ipy-auditlog
IPython のイベントフックを使い、コードセルの実行履歴を JSON Lines 形式で記録する軽量パッケージです。

## インストール

### 通常インストール（pip）

```bash
pip install ipy-auditlog
```

### 開発用インストール（このリポジトリをローカルで使う場合）

```bash
python -m pip install -e .
```

## 使い方

Jupyter Notebook / JupyterLab / IPython で extension を読み込みます。

```python
%load_ext ipy_auditlog
```

ログ収集を開始します。

```python
%auditlog_start test-analysis
```

この場合の出力先:

```text
.jupyter_audit/test-analysis.jsonl
```

引数を省略すると、現在日時（秒）ベースのファイル名が自動で使われます。

```python
%auditlog_start
```

状態確認:

```python
%auditlog_status
```

停止:

```python
%auditlog_stop
```

## ログ仕様（最小）

- 形式: JSON Lines（1イベント1行）
- 文字コード: UTF-8
- 拡張子: `.jsonl`
- 出力ディレクトリ: `.jupyter_audit/`
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
- `error`（失敗時は type / message / traceback）
