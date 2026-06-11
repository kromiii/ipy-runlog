# ipy-auditlog
IPython のイベントフックを使い、コードセルの実行履歴を JSON Lines 形式で記録する軽量パッケージです。

## インストール

### 通常インストール（pip）

```bash
pip install ipy-auditlog
```

### uv を使用する場合

#### プロジェクトの仮想環境にインストールする場合
```bash
uv pip install ipy-auditlog
```
または、`uv` プロジェクトに追加する場合:
```bash
uv add ipy-auditlog
```

#### `uv tool` を使用して IPython と一緒にインストール・実行する場合
`ipy-auditlog` は IPython 拡張機能であり、単体で実行可能な CLI を提供していません。そのため、`ipython` や `jupyter` などのツール環境に注入（インジェクション）して使用します。

* **IPython のツール環境にインストールする場合:**
  ```bash
  uv tool install ipython --with ipy-auditlog
  ```
* **一時的に実行する場合（`uvx` / `uv tool run`）:**
  ```bash
  uvx --with ipy-auditlog ipython
  ```

### 開発用インストール（このリポジトリをローカルで使う場合）

```bash
python -m pip install -e .
```
または `uv` を使用する場合:
```bash
uv pip install -e .
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

保存先ディレクトリを指定する場合は、`-d` または `--directory` を使用します。

```python
%auditlog_start test-analysis --directory ./logs
```

この場合の出力先:

```text
logs/test-analysis.jsonl
```

指定したディレクトリが存在しない場合は自動的に作成されます。相対パスは
IPython のカレントディレクトリを基準に解決されます。

引数を省略すると、現在日時（秒）ベースのファイル名が自動で使われます。

```python
%auditlog_start
```

保存先ディレクトリだけを指定することもできます。

```python
%auditlog_start --directory ~/auditlogs
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
- `error`（失敗時は type / message / traceback）
