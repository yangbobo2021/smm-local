# distribution: 同事试用分发

## 意图

让使用不同本机路径的同事能够安全安装和检查 SMM。

## 外部行为

### distribution-1

当用户从发行目录安装 SMM 时，系统应建立可运行环境并将同一 Skill 与 MCP 服务注册到本机已安装的 Codex 和 Claude Code。

### distribution-2

当用户重复安装相同版本时，系统应保留已有档案和用户设置，且不产生重复配置。

### distribution-3

当用户运行诊断时，系统应报告来源目录、数据库、服务、Skill、MCP 注册与导入状态，并明确区分本机接入检查与模型登录状态。

### distribution-4

当用户从另一绝对路径重新安装时，系统应更新其拥有的入口以指向新位置，且 Skill 不依赖开发者个人路径。

### distribution-5

当用户卸载 SMM 入口时，系统应停用服务并移除其拥有的 Skill 与 MCP 配置，同时保留已导入档案。

### distribution-6

当用户获取试用发行包时，发行包应只包含程序与说明，不包含用户对话、数据库或凭证。

### distribution-9

当系统为同一操作系统账户安装 SMM 时，安装器应在用户级安装清单中记录一个档案路径，供所有已安装的 Agent 和本机登录服务共享 [[access-10](access.md#access-10)]。

### distribution-11

当已安装的发行版 Skill 首次需要本机组件时，随附的启动脚本应在用户目录准备可用的 Python 环境并安装 SMM [[distribution-1](#distribution-1)]：

- 复用同一账户的可用安装和档案 [[distribution-2](#distribution-2)] [[distribution-9](#distribution-9)]。
- 从 Skill 随附的安装包安装，并在安装前校验其完整性 [[distribution-6](#distribution-6)]。
- 如果缺少可用的 Python，则通过固定版本的 uv 准备用户级 Python。
- 如果 MCP 注册或登录自启配置失败，则报告原因并保留可用的本机命令。
- 如果安装失败，则报告原因并允许下次使用时重试。

## 验证

### distribution-7

在干净用户目录安装、重复安装、搬迁安装、诊断与卸载时，应分别验证 [[distribution-1](#distribution-1)]、[[distribution-2](#distribution-2)]、[[distribution-3](#distribution-3)]、[[distribution-4](#distribution-4)] 与 [[distribution-5](#distribution-5)]。

### distribution-8

在封存发行包时，应核对文件清单与凭证扫描以验证 [[distribution-6](#distribution-6)]。

### distribution-10

在同一账户安装或更新两个 Agent 的入口时，验收应检查安装清单仅记录一个档案路径，并验证更新保留该路径 [[distribution-9](#distribution-9)]。

### distribution-12

在只放入发行版 Skill 的干净用户目录发起首次同步时，验收应检查本机组件由 Skill 准备，首个请求可以执行，两个 Skill 副本复用同一安装，且安装包损坏时拒绝安装 [[distribution-11](#distribution-11)]。
