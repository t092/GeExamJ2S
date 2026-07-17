# Stem 文字標記語法

用於在題幹（stem）中標記需要特殊格式的文字。

## 語法

```
__要加粗加雙底線的文字__
```

前後各兩個底線，包圍需要格式化的文字區段。

## 效果

- 雙底線（`text-decoration: underline double`）
- 粗體（`font-weight: bold`）
- 純黑色（`color: #000`）

## 範例

JSON 中的 stem 欄位：

```json
{
  "stem": "請閱讀以下文字：__這是需要強調的重點內容__，其餘為一般文字。"
}
```

前端渲染結果：

> 請閱讀以下文字：<u style="text-decoration:underline double;font-weight:bold;color:#000">這是需要強調的重點內容</u>，其餘為一般文字。

## 注意事項

1. `__` 必須成對出現，不可巢狀嵌套
2. 標記僅作用於 `stem` 欄位，不影響 `options`、`passage`、`explanation`
3. 目前僅 Q19 使用此標記，其他題目如有需要比照辦理即可
4. 無需修改前端程式碼，三套 renderer（engine.js / app.js / review.js）已內建支援
