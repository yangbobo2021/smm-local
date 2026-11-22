# PR #33 发现：Unicode 小写展开导致文档搜索范围错误

审查头：820fe2263a27bc747e5f7c635992906a63672bd8。独立 Reviewer 实际审查当前 diff，未改产品/测试。依据：已确认 SPEC B5/B6、A5。严重度 P2；性质为已确认产品缺陷，不是尚未完成的验收证据。

`src/smm_local/documents.py:380–381` 在 `text.lower()` 上计算 `find` 位置，再将该位置用作原始采集文本的 Unicode 码点坐标。U+0130 LATIN CAPITAL LETTER I WITH DOT ABOVE（İ）转小写得到两个码点 `i` + U+0307，使后续位置偏移。

实际复现命令（隔离临时目录及新档案，无Hub、无用户资料）：

```sh
.venv/bin/python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from smm_local.core import Archive
from smm_local.documents import Documents
with TemporaryDirectory(prefix='smm-pr33-review-unicode-') as td:
    p=Path(td)
    f=p/'unicode.txt'
    f.write_text('İ'*3000+' needle tail',encoding='utf-8')
    d=Documents(Archive(p/'archive.sqlite3'))
    s=d.add(str(f))
    print('refresh status',d.refresh(s['id'])['sources'][0]['status'])
    try:
        r=d.search('needle')
        print('results',len(r['results']),[(x['start'],x['end'],'needle' in x['text']) for x in r['results']])
    except Exception as e:
        print(type(e).__name__,str(e))
PY
```

真实 stdout：

```text
refresh status ready
ValueError 范围须为整个采集文本的Unicode码点 [start,end)，一次1至16000字符
```

该诊断命令捕获并打印异常，因此命令退出码为0；这不是产品搜索成功的证据。源文件是6012字节严格UTF-8文本，规范文本3012码点，未触及任何预算。实际needle原偏移3001，小写文本偏移6001，产品窗口start=5801、end=3012，故范围验证拒绝。CLI/API同样调用该共享后端，整个搜索会失败；较短展开前缀亦可能使2000码点窗口离开真正命中位置。

影响：用户合法纳入、成功刷新的长文档无法通过普通内容词检索/读回准确位置，违反长行/长文及码点位置约定。建议把大小写匹配位置映射回原文坐标，保持现有分词语义；独立回归应检查展开字符、非BMP/组合字符、靠后匹配的search窗口含实际词，search→read的文本/码点/行号等于独立源字符串计算结果。

修复后再审同一实现PR；本发现不要求改动已确认规格，不允许用放宽输入或Unicode语义替代修复。最终验收须更新真实受产品字节变化影响的共享及三平台轮次。
