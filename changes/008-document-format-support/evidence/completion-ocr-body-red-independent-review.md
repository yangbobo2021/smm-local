# OCR正文质量独立红灯复审

结论：`expected_failure`。本版候选设计有效，原产品在清晰扫描正文将 `73428` 识别成 `/3428`，CER `1/48 = 2.083333%` 超过A5的1%。

场景与设计有效：已实际读AGENTS.md、008 intent/spec/plan、定义000003及本版设计/匹配/runtime。SC5质量判据逐字对应SPEC A5(185行)，B3(43–51行)承诺清晰水平中英文印刷文字，C1(198行)要求独立真值、全部目标和Levenshtein/仅空白归一；无网格正文属于B3，不要求伪造网格。新增正文补已知失败，不替代原双份双页中英网格；正式命令仍同时跑test_document_formats_pdf_ocr.py与test_document_formats_ocr_body_quality.py。故障/无网/完整E/H/X不在本红灯认领范围，设计已保留gap与分工。独立核69 bindings/84 artifacts全SHA相符，ocr.py=4077d0d00a30299e6d2fdca3b138f4338539cf40b825a5c42f2faa02ff0f550e，未改产品/测试。绘制源retry.py:27–33于2000×600白底绘制两行，再嵌入600×180 PDF；独立固定预期在body_quality.py:21–28，不取自产品。实用同版冻结字体重绘四份PDF及网格truth，均逐字相同；实际渲染查看四份六页，均无原生文字层，正文73428清晰为7，第二行12345.67清晰，全部中文网格/金额与源真值对应。LOCAL原SHA c1f3d3c6950fa0a7bf6cf2f62aba9967193f2f296ee108c434e6ae996e63bded，HUB原SHA 3e360990a95acc3ca04ad391500fbaa235b17b12e946ce5d8e718d4c8536ccea，二者也分别与保留debug8原件逐字一致。标签不代表Hub执行身份，均为Local公开API/CLI共享C1。

边界反例走查：仅首文件成功时，原测试39–40先核完整文件集合和各状态，45行拦漏/重复命中，46–49逐文件独立全文，第二文件错值再由75行逐格真值拦截；新正文参数化14行覆盖两份，各自35行原SHA/42行独立全文拦截第二目标错误。仅首页面/表成功会被52行两表唯一集合、54–59逐页标题/正文精确定位、67行每页单表及71–78全坐标/逐格内容框拦截；两边同错/同用首档，即便搜索和读取一致，仍被原49/50/75行独立文本/SHA/格值或正文35/42/44行拦截。状态方面本质量用例限定配置已就绪的首次真实采集，41行拒非ready/errors；缺组件、超时、取消和重处理前状态由已列gap的其他TC承担，不能把本候选当整场景闭环。未见有依据而会改变本质量预期、且现有断言可全过的遗漏。

实际红灯可信：run.stdout为1 failed/3 passed/8.00s、exit1；原双页网格实项和真值自检均过，alpha/beta CER=0，每份2页2表12格；HUBSCANGAMMA正文CER=0且完成原件下载相等。LOCAL实际全文为“LOCALSCANGAMMA RETRY/3428\nCAPTURED ORIGINAL 12345.67”，独立预期为“LOCALSCANGAMMA RETRY 73428\nCAPTURED ORIGINAL 12345.67”，仅去空白后48字符，替换7→/一次，CER=1/48=2.083333%>1%。先前35行身份/SHA及41行ready/errors均已通过，在42行业务CER断言失败；73428关键标识也实际错误。无环境/import/组件缺失或测试异常可解释该失败，因此授予expected_failure。LOCAL后续43–58行的关键检索、无表、精确行定位、下载及最终mtime断言未到达；其原件已在inputs留存但无本次download，不认这些后续项已通过。观察JSON虽可见两OCR行、页面尺寸、区域与置信，但不替代未到达断言。历史debug8失败保持，不因HUB或其他更清晰材料通过而注销。本意见只判本版候选和原产品红灯，不审未应用方案，也无正式green结论。

证据核验：69个绑定、84个产物全部摘要一致。四份PDF源重绘逐字一致，原网格truth重建一致；实际查看6页渲染。完整逐文件SHA、目标收据摘要与范围限制见同名JSON。

关键摘要：

- `.acceptance/native-v1/AT-SMM-008/definitions/000003.json`: `16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`
- `.acceptance-local/native-v1/AT-SMM-008/tdd-red/red-completion-sc5-body-quality-v1/result.json`: `10d4cdf471ef7b2dd5c3006cd4809eb6939c24414f3b5702fd43a7bf5b016305`

审查意见：`.acceptance-local/native-v1/AT-SMM-008/review-inbox/review-completion-sc5-body-quality-red-v1.json`。
