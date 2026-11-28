# GC 读取共享 v2 红灯独立复审

**结论：expected_failure。** AT-SMM-008 / SC8，仅实际TC-008-gc-read-sharing；不认领场景检查ID。目标摘要`98dfe1acea853e666d7aeca0f37171603f7e646507370979c14a05473b7e281f`。已写原生意见`review-completion-sc8-gc-read-sharing-red-v2.json`，可登记后进入产品实现。

## 需求与设计检查

沿本轮已读AGENTS、008 intent/spec/plan、交付验收SKILL及development/reviewer/design规则，并再次核SPEC B5和A8原文。合法更新、连续采集资格、旧发布与失效身份不复活均有依据；元信息并发读不应导致正常发布失败属于这些行为的共享组件回归。设计v1允许短读释放后有界串行，测试125行0.2秒自动释放不增加“writer须在门内完成”条件。旧SC8七TC仍按v1保留；本次仅审新增组件TC，完整网页链与生命周期另验。

## 冻结版本和来源检查

match v4、runtime v3及红灯v2均引用定义`16154976ac894fc68f2abcd148273bcea3e506391192896b262d6a78cba69633`与同一自然设计v1。测试SHA`e410518472b861e354771dc55b426bbc7bb3fb9e9bc9108594a195100cb9f866`。已核全部287项native artifacts、输入226源及Windows before/after摘要，无不符。所有64产品文件与Git e233848逐字相同，当前未应用草稿补丁。

原output.tar.gz为75167字节，SHA`0530d2c986d8be4ee4faf133986434fd9f0de582c1d8809b69a9443b06d432fd`，与远端传输长度/SHA一致；所有普通tar成员逐字与verified一致。两个pytest current symlink保留在原tar，archived-links.json记录准确；verified未重建链接、未跟随。SSH create/upload/download/receipt均0；business实际1，与Windows结果一致；外层与远端run.stderr均空。运行器不再掩盖本次业务失败。

## 测试设计与实现检查

67–81行：真实DOCX两次公开refresh（Fixture的实际HTTP入口）产生V/P2 ready、不同CID，以及含真实成员的archives/owners/retired；核原档案身份、数据库路径、原退休CID/AID与当前raw键。仅项目夹具通过既有project存储建立项目，未直写文档捕获/处理状态。

83–100行：archives以同父目录新独立Archive实际登记添加第二身份；owners以确定性ZIP第三份DOCX调用真实Snapshots.put添加新raw SHA；retired经公开remove再reclaim添加当前失效CID/AID。预先从磁盘独立冻结完整旧值、保留旧全集构造完整新预期，100行保证确有不同新代。真实门控不修改文件flags、atomic_json或异常。

117–122行：实际进程树找到marker的PID/ctime，精确argv包含隔离UUID源码、数据库、目标JSON和门；same_existing_path比较同一实际exe，修复旧的大小写误拒绝。marker在真实stream.read调用前记录真实descriptor=3与路径；不是人工打开另一个假句柄，也不把venv launcher当Python本体。

135–143行：正常读退出、完整旧值、writer成功、每个元信息直接磁盘JSON与产品读均等于独立完整新/旧预期，最后核源原件SHA/大小/mtime及无关文件bytes/mtime。能拦截两端同丢既有成员、只保留新CID/AID而遗失旧永久集合、未写新代、更新错目标及篡改非目标状态。v1空旧集合和仅复用被测读取的缺口已补；不要求再添同条件等价身份样例。

## Windows 实际首次失败检查

实际win32、Python3.14.10、is_admin=true，限定组件证据。原run.stdout：**3 failed, 1 passed, 11.71秒**。archives、owners、retired三参数均首次失败在137行`assert error is None,error`。126行实际writer已执行；原attachments的writer_error均为PermissionError/WinError5，明示对应JSON临时文件→同名正式文件的替换失败。

分别绑定launcher→真实reader为3044→17264、3216→12648、14792→11400，均有ctime、完整argv和目标句柄。135/136行已通过，真实reader退出0并返回完整独立旧值。旧archives有1成员、新预期2；owners旧4、新5；retired新预期为旧captures/attempts集合加这次失效身份，旧集合分别保留。独立打开tar中失败后的三个元信息，也均仍等于各自旧完整值；这只是失败后保护观察，不能代替新代成功。

第三方不合作句柄正控实际通过150–153行：WinError5、旧值仍在、关闭句柄后替换成功。它证明真实Windows共享拒绝路径，不冒充产品行为；本次产品红灯来自前三项自己的writer错误。

**未到达：138–143行。** 新代全集、其他元信息不变、原件fingerprint及unrelated文件保护已在源码中落实，但本轮因137首败而未执行，不能认通过。它们应由同版绿灯实际完成。

## 既往记录及范围检查

Mac同版开发前stdout为3通过、1Windows-only跳过、2.01秒，仅作开发前旁证，不能代Windows。runtime-v2仍为blocked，其原stderr为本地verified目录已存在的FileExistsError；runtime-v3采用新UUID并ready。v1路径观察器和链接采证失败仍是needs_revision，不改变旧结论。

本次没有执行新业务、修改产品/测试或应用草稿。gc-read-lock-draft.patch仅作只读理解，不参与红灯判定。正式结论只证明未改产品在真实Windows自有metadata reader与writer并发下缺失本组件要求；不关闭普通E账户、SCM/LocalService、实际Web更新、完整生命周期或E/H/X矩阵。产品实现后需同冻结测试/命令绿灯及相关回归，再取新的独立绿灯意见。
