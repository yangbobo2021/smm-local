# Unicode 返修中间方案复审（尚未提交）

当前尝试将 lower().find 改为原文本 re.search(..., re.IGNORECASE)。它避免坐标展开，但Python IGNORECASE还把 U+0131 dotless i 与ASCII i、U+017F long s与ASCII s等视为相等，比core.tokens(text.lower())的既有语义更宽，可能把预览移到真实内容命中之前。

独立隔离复现：新临时TXT内容 `'ı'*3000+' i tail'`，add/refresh ready，search('i')。真实stdout为 `start/end 0 2000 query in snippet False last text 'ıııııııııııı'`。实际i在原文3001码点；FTS因尾部i召回文档，但正则把开头无点ı当作i，返回前2000个无点ı，read与同窗口一致却不覆盖真实召回词。命令正常退出0；没有改代码或断言。

同一P2仍开放：需要保留tokens的小写内容语义，并将匹配偏移映射回原文本码点。若采用其他方案，需独立核对以上反例及原İ展开反例后再关闭。
