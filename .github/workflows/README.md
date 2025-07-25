# GitHub Actions ワークフロー

このディレクトリには、Obsidian→WordPress自動投稿システムのワークフローが含まれています。

## 📝 メインワークフロー

### pr-tasks.yml
ブランチ更新時に実行されるワークフロー

- 下書き記事のWordPress投稿
- 記事品質チェック
- HTMLプレビュー生成

### publish-article.yml
PRマージ時に記事を公開状態に変更し、`articles/drafts` → `articles/published` へ移動

- 重複投稿の防止（既存記事の更新）
- 処理結果のPRコメント投稿
- 詳細なサマリーレポート

## 🖼️ 画像処理

### image-optimize.yml
画像の自動最適化

- PNG/JPG → WebP変換（GIFは除外）
- ファイルサイズの削減
- SEO最適化されたファイル名への変換
- 自動コミット

## 📊 定期実行ワークフロー

### backup-articles.yml
WordPressの記事を定期バックアップ（毎週日曜日）

- すべての投稿をJSON形式で保存
- 30日以上前のバックアップは自動削除
- ステータス別の集計情報

### analytics.yml
記事の統計レポート生成（毎週日曜日）

- 記事数、カテゴリ、タグの集計
- 月別投稿数の推移
- ビジュアル化されたグラフ生成

## 🔧 セットアップ

必要なGitHub Secrets:
- `WP_URL`: WordPressサイトのURL
- `WP_USERNAME`: WordPressユーザー名
- `WP_APP_PASSWORD`: アプリケーションパスワード

## 💡 使い方

1. `articles/drafts/` に記事を作成
2. PRを作成すると自動的に下書き投稿
3. レビュー後、マージすると自動公開
4. 記事は `articles/published/YYYY/MM/` に移動

## 🚀 今後の改善案

- [ ] 記事のSEOスコア自動チェック
- [ ] 関連記事の自動リンク生成
- [ ] ソーシャルメディアへの自動投稿
- [ ] アクセス解析との連携